# core/memory_claims.py — UNIQUE HOST
#
# COMPARE AND CONFIRM: what the user CLAIMS about the past is checked against the
# events the host actually stored (same finder as core/memory_recall.py).
#
#   "Did you see the monster yesterday?"      -> "Yes. I remember the monster..."      (confirm)
#   "Were you scared of the monster?"         -> stored as bad  -> "Yes.... It scared me."
#                                             -> stored as good -> "No.... It felt good." (correction)
#   "The monster attacked you."               -> stored as bad  -> "That's right...."
#   "You liked the monster."                  -> stored as bad  -> CONTRADICTION: "That's not how it was..."
#   "Did you see the dragon?"                 -> nothing stored -> "I don't remember the dragon."
#
# A CONTRADICTION here works like the identity check that corrects the age
# ("You are 40" -> "I am 25 years old", core/pre_input.py:detect_identity_contradiction):
# cycle_manager_v5 puts it in `contradiction_info` (contradiction_type = "memory") and
# output/phrase_builder.py:build_contradiction_phrase returns its phrase.
#
# A message is treated as a claim only if it is (1) about the host or the user
# ("you", "me", "we"...), (2) in the past (past-tense verb or a time expression) and
# (3) not already a recall request ("Do you remember...?", handled by memory_recall.py).
# Present-tense roleplay ("<<the monster attacks>>") is never a claim.
#
# Polarity (good / bad) of the claim comes from a small CLOSED word list below —
# the lexicon's emotional tags are empty for most words, so they can't be used.
# The list is a draft to extend. Unknown polarity never contradicts:
# it only confirms that the thing was stored.

import core.memory_recall as mr

NEGATIVE_WORDS = {
    "attack", "hurt", "kill", "scare", "scared", "frighten", "frightened", "terrify", "terrified",
    "fear", "afraid", "threaten", "chase", "wound", "injure", "bite", "hit", "fight", "hate",
    "dislike", "angry", "panic", "panicked", "flee", "harm", "bad", "danger", "dangerous",
    "cruel", "cry", "scream", "suffer", "betray", "steal", "trap",
}
POSITIVE_WORDS = {
    "help", "save", "protect", "rescue", "like", "love", "enjoy", "safe", "calm", "happy",
    "glad", "friendly", "kind", "comfort", "laugh", "smile", "trust", "hug", "thank", "warm",
    "good", "gentle", "care", "welcome", "cheer", "relieved", "peaceful",
}
# Verbs that make "Did you ___ the X?" a question about an EXPERIENCE. Without one of these (or
# a time expression, or a good/bad word) the host doesn't answer "I don't remember" -- "Did you eat?"
# resolves to the concept `food` and must not become "I can't place the food".
EXPERIENCE_VERBS = {"see", "meet", "hear", "notice", "watch", "encounter", "face", "find", "visit",
                    "know", "happen", "follow", "remember", "touch", "feel"}
_AUX_START = {"did", "do", "does", "were", "was", "have", "has", "had", "are", "is", "can", "could"}
_NON_SUBJECT_TYPES = {"action", "quality"}   # "I don't remember the eat" is never said


def _polarity(doc):
    """('negative'|'positive'|None, set of polarity words). A negation flips the result."""
    found, words = None, set()
    for t in doc:
        for form in (t.lemma_.lower(), t.text.lower()):
            if form in NEGATIVE_WORDS and found is None:
                found = "negative"; words.add(t.text.lower())
            elif form in POSITIVE_WORDS and found is None:
                found = "positive"; words.add(t.text.lower())
    if found and any(t.dep_ == "neg" for t in doc):
        found = "positive" if found == "negative" else "negative"
    return found, words


_CONTRADICTION_T = [
    "That's not how it was. {Np}{when}... {feeling}",
    "No. That's not what I remember. {Np}{when}: {feeling}",
]
_QUESTION_NO_T = ["No. {Np}{when}... {feeling}", "Not really. {Np}{when}... {feeling}"]


def _stored_valence(ccm, subject, events):
    """Valence of what is stored about `subject`. For the user (many events) the majority wins."""
    user = mr.present_name(ccm)
    if subject == user:
        pos = sum(1 for _, e in events if e.get("valence") == "positive")
        neg = sum(1 for _, e in events if e.get("valence") == "negative")
        return "positive" if pos > neg else "negative" if neg > pos else "neutral"
    return events[0][1].get("valence") or "neutral"


def check_claim(ccm, raw_text: str, concepts: list):
    """
    Returns None (not a claim about the past, or nothing to say) or a dict:
      {"kind": "confirm" | "contradiction" | "unknown", "phrase", "subject", "found",
       "claimed", "stored", "action"}
    """
    if not raw_text or mr.detect_recall_query(raw_text):
        return None
    from core.construction_matcher import get_nlp
    from db.db_concepts import CONCEPTS
    doc = get_nlp()(raw_text)
    low = [t.text.lower() for t in doc]
    user = mr.present_name(ccm)

    addressed = any(w in ("you", "your", "yours", "yourself") for w in low)
    about_user = bool(user) and any(w in ("me", "i", "my", "we", "us", "our") for w in low)
    time_bucket = None
    for bucket, pat in mr._TIME_PATTERNS:
        if pat.search(raw_text):
            time_bucket = bucket
            break
    past = bool(time_bucket) or any(
        t.tag_ in ("VBD", "VBN") or (t.lemma_ in ("do", "be", "have") and t.tag_ == "VBD") for t in doc)
    if not (addressed or about_user) or not past:
        return None

    is_question = raw_text.strip().endswith("?") or (low and low[0] in _AUX_START)
    claimed, polarity_words = _polarity(doc)

    time_words = mr._time_words(raw_text)
    content = [c for c in mr._content_concepts(ccm, concepts)
               if c not in time_words and c not in polarity_words
               and c not in NEGATIVE_WORDS and c not in POSITIVE_WORDS]
    universe = set()
    for _, e in mr._all_events(ccm):
        universe.update(e.get("concepts", []))
    for tok in mr._tokens(raw_text):
        if tok in universe and tok not in content and tok not in mr._QUESTION_WORDS \
                and tok not in time_words and tok not in polarity_words:
            content.append(tok)
    if about_user and user not in content:
        content.append(user)
    remembered = [c for c in content if c in universe]

    experience = bool(claimed) or bool(time_bucket) or any(t.lemma_.lower() in EXPERIENCE_VERBS for t in doc)
    if not remembered:
        if not experience:
            return None
        nouns = [c for c in content if c != user and CONCEPTS.get(c, {}).get("type") not in _NON_SUBJECT_TYPES]
        if is_question and nouns:
            np_ = mr._noun_phrase(ccm, nouns[0])
            return {"kind": "unknown", "found": False, "subject": nouns[0], "claimed": claimed, "stored": None,
                    "phrase": mr._pick(ccm, "no1", mr._NOTHING_ABOUT_T).format(np=np_, Np=mr._cap(np_)),
                    "action": f"trying to remember {np_}"}
        if time_bucket and nouns:                      # a dated claim we have nothing on
            return {"kind": "unknown", "found": False, "subject": nouns[0], "claimed": claimed, "stored": None,
                    "phrase": "I don't remember that.", "action": "trying to remember"}
        return None                                    # plain narration by the user: not ours to judge

    matches = mr.find_events(ccm, remembered, time_bucket)
    if not matches:
        return None
    tier, event = matches[0]
    subject = next((c for c in event.get("concepts", []) if c in remembered), remembered[0])
    stored = _stored_valence(ccm, subject, matches)
    np_ = mr._noun_phrase(ccm, subject)
    base = {"subject": subject, "found": True, "claimed": claimed, "stored": stored, "tier": tier,
            "action": f"remembering {np_}"}

    if claimed and stored in ("positive", "negative") and claimed != stored:
        shown = dict(event, valence=stored)
        fmt = {"Np": mr._cap(np_),
               "when": " " + (mr._WHEN["long"] if event.get("closed_at") is None else mr._WHEN[tier]),
               "feeling": mr._feeling(ccm, shown)}
        options = _QUESTION_NO_T if is_question else _CONTRADICTION_T
        return dict(base, kind="contradiction", phrase=mr._pick(ccm, "claim-no", options).format(**fmt))

    desc = mr._describe(ccm, tier, event, subject)
    lead = "" if desc.startswith("Yes") and is_question else ("Yes. " if is_question else "That's right. ")
    return dict(base, kind="confirm", phrase=lead + desc)
