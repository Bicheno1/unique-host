# core/memory_recall.py — UNIQUE HOST
#
# MEMORY RECALL ON REQUEST — "Do you remember the monster?", "Do you remember
# yesterday?", "What do you think about me?"
#
# The character answers by RE-CREATING a stored event: it finds the events in
# memory that match the question, then fills a closed template with the focus
# subject, how the event felt (its stored valence + strength) and when it
# happened. Same design as the rest of UNIQUE HOST: a closed repertoire of
# slot templates, no free generation.
#
# Three kinds of question are recognised (regex on the raw text, no NLP needed):
#   1. SUBJECT  "Do you remember the monster?"  -> events that contain "monster"
#   2. TIME     "Do you remember yesterday?"     -> events from that time bucket
#   3. ABOUT ME "What do you think about me?"    -> events that contain the
#               name of whoever is speaking now (see present_name): the feeling is the average of them
# Time and subject can be combined ("Do you remember the monster from yesterday?").
#
# TIME is measured in tiers, not wall-clock: roleplay time has no clock, and
# the memory system already ages events into short -> medium -> long/nuclear.
#     recent  ("just now", "earlier")            -> short-term first
#     past    ("yesterday", "last time")         -> medium-term first
#     distant ("long ago", "as a child")         -> long-term / nuclear first
# If the wanted tier is empty, the other tiers are tried and the answer says
# when the event REALLY was ("a while back"), it never invents a time.
#
# Wording below is a first draft to review (same as the phrase bank).

import random
import re

# ── 1. DETECTION ─────────────────────────────────────────────────────────────

_REMEMBER = re.compile(
    r"\b(?:remember|remembered|recall|recalled)\b(?!\s+to\b)|\bhave you forgotten\b|\bdid you forget\b",
    re.I)
_ABOUT_ME = re.compile(
    r"\b(?:think|thought|feel|felt|say|know)\s+(?:of|about)\s+(?:me|us)\b"
    r"|\bwhat (?:am|are) (?:i|we) to you\b|\bwho am i to you\b"
    r"|\bdo you (?:like|trust|love|hate|fear|miss|know)\s+me\b"
    r"|\bhow do you (?:see|feel about)\s+me\b"
    r"|\b(?:remember|recall)\s+(?:me|us)\b",
    re.I)
_WHAT_HAPPENED = re.compile(r"\bwhat (?:happened|did (?:we|you|i) do)\b", re.I)

# Time expressions -> bucket. Checked distant -> recent -> past so the most
# specific phrase wins ("a long time ago" must not match "a while ago").
_TIME_PATTERNS = (
    ("distant", re.compile(
        r"\b(?:long ago|a long time ago|years ago|ages ago|back then|as a (?:child|kid)|"
        r"when you were (?:young|little|small|a child)|in the old days|when we first met|"
        r"the first time|childhood)\b", re.I)),
    ("recent", re.compile(
        r"\b(?:just now|(?:a )?(?:moment|second|minute|little while|bit)s? ago|moments ago|"
        r"a few minutes ago|earlier|this morning|today|tonight)\b", re.I)),
    ("past", re.compile(
        r"\b(?:yesterday|last night|the other day|the day before|last time|last week|"
        r"days ago|a while ago|some time ago|recently)\b", re.I)),
)

# Tier search order per bucket (first = the tier the question points at).
_TIER_ORDER = {
    "recent":  ("short", "medium", "long"),
    "past":    ("medium", "long", "short"),
    "distant": ("long", "medium", "short"),
    None:      ("long", "medium", "short"),
}
# How an event's tier reads when the answer says WHEN it happened.
_WHEN = {"short": "just now", "medium": "a while back", "long": "a long time ago"}

# Words that are part of the question itself, never the thing being asked about.
_QUESTION_WORDS = {"you", "do", "does", "did", "remember", "recall", "what", "who", "how",
                   "which", "where", "me", "us", "we", "i", "yesterday", "today", "earlier",
                   "tonight", "ago", "think", "about", "of", "that", "it", "anything"}


def _time_words(raw_text: str) -> set:
    """Tokens of the time expression itself ('a long time ago') -- never a memory subject."""
    words = set()
    for _, pat in _TIME_PATTERNS:
        for m in pat.finditer(raw_text or ""):
            words.update(re.findall(r"\w+", m.group(0).lower()))
    return words


def detect_recall_query(raw_text: str):
    """
    Returns None (not a recall question) or a dict:
      {"kind": "about_me" | "remember", "time": "recent"|"past"|"distant"|None}
    """
    if not raw_text:
        return None
    text = raw_text.strip()
    time_bucket = None
    for bucket, pat in _TIME_PATTERNS:
        if pat.search(text):
            time_bucket = bucket
            break
    if _ABOUT_ME.search(text):
        return {"kind": "about_me", "time": time_bucket}
    if _REMEMBER.search(text) or _WHAT_HAPPENED.search(text):
        return {"kind": "remember", "time": time_bucket}
    return None


# ── 2. FINDING MEMORIES ──────────────────────────────────────────────────────

def present_name(ccm) -> str:
    """Lower-case name of the person the host is talking to RIGHT NOW: the named speaker of this
    message ("Joaquin", "bandit") or, for the narrator / "user" speakers, the name the player gave
    (ccm.user_name). "" if nobody is named. cycle_manager_v5 sets ccm._present_name on every turn;
    without it (direct calls) ccm.user_name is used."""
    name = getattr(ccm, "_present_name", None) or getattr(ccm, "user_name", None)
    return name.lower() if name else ""


def _all_events(ccm):
    """Every stored event as (tier, event). Somatic and mental memories are merged,
    de-duplicated by (concepts, closed_at, class)."""
    seen, out = set(), []
    for mem in (ccm.memory_m, ccm.memory_s):
        # A threat episode still in progress (it closes after 2 quiet cycles) is already something the
        # host lived: "Do you remember the monster?" one turn after it must not answer "I can't place it".
        if getattr(mem, "_thr_active", False) and mem._thr_concepts:
            import systems.memory_system as _ms
            peak_c = max(mem._thr_peak_m, mem._thr_peak_C)
            peak_d = max(mem._thr_peak_s, mem._thr_peak_D)
            ec = _ms._max_class(_ms._classify(mem._thr_peak_m, mem._thr_peak_s), _ms._classify(peak_c, peak_d))
            if ec:
                e = {"concepts": _ms._key(mem._thr_concepts), "event_class": ec, "is_nuclear": False,
                     "mental_peak": peak_c, "somatic_peak": peak_d, "valence": "negative",
                     "closed_at": mem._cycle, "source": "threat", "open": True}
                k = (tuple(e["concepts"]), e["closed_at"], ec, "short")
                if k not in seen:
                    seen.add(k)
                    out.append(("short", e))
        # The window itself: what was said in this scene and has not been flushed to short term yet.
        # Turns of the CURRENT cycle are left out, or "Do you remember the city?" would remember itself.
        if hasattr(mem, "window_turns"):
            ev = mem.context_event(mem.window_turns(before_cycle=mem._cycle))
            if ev:
                ev = {**ev, "open": True}
                k = (tuple(ev["concepts"]), ev["closed_at"], ev["event_class"], "short")
                if k not in seen:
                    seen.add(k)
                    out.append(("short", ev))
        for tier, events in (("short", mem.short_term), ("medium", mem.medium_term),
                             ("long", mem.long_term)):
            for e in events:
                k = (tuple(e.get("concepts", [])), e.get("closed_at"), e.get("event_class"), tier)
                if k in seen:
                    continue
                seen.add(k)
                out.append((tier, e))
    return out


def _ev_concepts(e):
    """Everything an event can be asked about: its 5-concept key plus, for context chunks, all they held."""
    return set(e.get("concepts", [])) | set(e.get("all_concepts", []))


def _significance(e):
    s = e.get("mental_peak", 0.0) / 200.0 + e.get("somatic_peak", 0.0) / 400.0
    return s + (0.5 if e.get("is_nuclear") else 0.0)


def _is_strong(e):
    return bool(e.get("is_nuclear")) or e.get("event_class") in ("large", "major")


def _content_concepts(ccm, concepts):
    """Concepts of the question that can be the SUBJECT of a memory."""
    from db.db_concepts import CONCEPTS
    me = (ccm.character_name or "").lower()
    out = []
    for c in concepts:
        if c in _QUESTION_WORDS or c == me or c in out:
            continue
        if CONCEPTS.get(c, {}).get("type") == "language":
            continue
        out.append(c)
    return out


def _tokens(raw_text):
    return [re.sub(r"[^\w]", "", re.sub(r"'s$", "", t)) for t in raw_text.lower().split()]


def find_events(ccm, wanted_concepts, time_bucket):
    """Events matching ANY wanted concept (or all events if none wanted), ordered
    by: tier the question points at, then whether it is a real tracked episode (threat/arc) vs a plain
    context chunk, then number of matching concepts, then significance. Returns a list of (tier, event).

    The context-chunk/tier tie-break exists because a context chunk can span several turns of MIXED
    sign (an ambush, then relief when the attacker flees), and _event_valence() reads only its single
    biggest-magnitude turn -- so its valence can come out reversed from what the concept's own dedicated
    threat/arc episode correctly recorded. A context chunk with a big peak must never outrank a real
    episode that covers the same concept just because its raw numbers are larger; it is a fallback for
    concepts that have NO dedicated episode (going/market), not a competing answer for ones that do.
    """
    order = _TIER_ORDER[time_bucket]
    want = set(wanted_concepts)
    scored = []
    for tier, e in _all_events(ccm):
        overlap = len(want & _ev_concepts(e)) if want else 0
        if want and not overlap:
            continue
        is_context = 1 if e.get("source") == "context" else 0
        # a closer closed_at (cycle) is a tiny tie-breaker: newer first
        recency = (e.get("closed_at") or 0) / 1e6
        scored.append((order.index(tier), is_context, -overlap, -(_significance(e) + recency), tier, e))
    scored.sort(key=lambda x: x[:4])
    return [(t, e) for _, _, _, _, t, e in scored]


# ── 3. TEMPLATES (closed repertoire, draft wording) ──────────────────────────

_FEELING = {
    ("negative", False): ["It didn't sit right with me.", "I didn't like it.", "It left a bad taste."],
    ("negative", True):  ["It scared me. I can still feel it.", "I'll never forget how bad that was.",
                          "It still hurts to think about it."],
    ("positive", False): ["It felt good.", "It was a good moment.", "I liked it."],
    ("positive", True):  ["It meant a lot to me.", "I hold on to that.", "It's one of the good ones."],
    ("neutral",  False): ["It didn't stir much in me.", "It's a bit of a blur."],
    ("neutral",  True):  ["It's hard to say what I felt.", "It stays with me, I can't say why."],
}

# {np} noun phrase, {Np} same capitalised, {when} " a while back" or "", {other} optional extra
_REMEMBER_T = [
    "I remember {np}{when}. {feeling}",
    "I do remember {np}{when}. {feeling}",
    "{Np}{when}... yes. {feeling}",
    "Yes, {np}{when}. {feeling}",
]
_REMEMBER_WITH_T = [
    "I remember {np}{when}, and {other}. {feeling}",
    "{Np}{when}, and {other}... yes. {feeling}",
]
_NOTHING_ABOUT_T = ["I don't remember {np}.", "{Np}? Nothing comes to mind.", "I can't place {np}."]
_NOTHING_TIME_T = ["I can't remember anything from then.", "Nothing comes to mind from then."]
_NOTHING_AT_ALL_T = ["I don't remember much at all.", "Nothing stands out."]

_ABOUT_ME_NONE = ["I don't know you well enough yet.", "We haven't been through much together.",
                  "You're still a stranger to me."]
_ABOUT_ME_POS = ["Things go better when you're around. I like that.",
                 "You've been good to have around. I remember.",
                 "I trust you more than I let on."]
_ABOUT_ME_POS_STRONG = ["You mean a lot to me. What we went through together stays with me."]
_ABOUT_ME_NEG = ["Things tend to go wrong when you're around. That worries me.",
                 "I remember what happened with you. It wasn't good."]
_ABOUT_ME_NEG_STRONG = ["You scare me a little. What happened with you, I can't shake it."]
_ABOUT_ME_MIXED = ["I'm not sure yet. Some of it was good, some of it wasn't.",
                   "It's complicated. We've had good moments and bad ones."]


def _pick(ccm, key, options):
    """Random choice that avoids repeating the last variant used for `key` (per session)."""
    memo = getattr(ccm, "_recall_last", None)
    if memo is None:
        memo = ccm._recall_last = {}
    choices = [o for o in options if o != memo.get(key)] or options
    pick = random.choice(choices)
    memo[key] = pick
    return pick


def _known_names(ccm):
    """lower-case concept -> display name, for proper nouns (user, family, pet, friend)."""
    names = {}
    present = present_name(ccm)
    if present:
        names[present] = present[:1].upper() + present[1:]
    try:
        import motors.core_identity as core_identity
        for rule in core_identity.CORE_RULES.values():
            val = rule.get("value")
            if isinstance(val, dict):
                for k in ("name", "father", "mother", "pet", "friend"):
                    if isinstance(val.get(k), str) and val[k]:
                        names[val[k].lower()] = val[k]
            if rule.get("type") == "relationship" or rule is core_identity.CORE_RULES.get("custom_friend"):
                for c in rule.get("concepts", []):
                    if isinstance(c, str):
                        names.setdefault(c.lower(), c[:1].upper() + c[1:])
    except Exception:
        pass
    return names


def _noun_phrase(ccm, concept):
    """'you' for the user, 'Bruno' for known names, 'the monster' for everything else."""
    user = present_name(ccm)
    if user and concept == user:
        return "you"
    names = _known_names(ccm)
    if concept in names:
        return names[concept]
    from core.construction_matcher import _add_article
    return _add_article(concept, is_proper=False)


def _cap(s):
    return s[:1].upper() + s[1:]


def _feeling(ccm, event):
    return _pick(ccm, "feel", _FEELING[(event.get("valence") or "neutral", _is_strong(event))])


def _describe(ccm, tier, event, subject):
    """Fills the REMEMBER template for one event."""
    np_ = _noun_phrase(ccm, subject)
    # seeded events (core fear/comfort) have no real time -> always "a long time ago"
    when = " " + (_WHEN["long"] if event.get("closed_at") is None else _WHEN[tier])
    user = present_name(ccm)
    from db.db_concepts import CONCEPTS as _C
    # an action ("going") is not a second topic: "the city, and the going" reads wrong
    others = [c for c in list(event.get("concepts", [])) + list(event.get("all_concepts", []))
              if c != subject and c != user and c not in _QUESTION_WORDS and c not in _MOTION
              and _C.get(c, {}).get("type") != "action"]
    fmt = {"np": np_, "Np": _cap(np_), "when": when, "feeling": _feeling(ccm, event)}
    if others:
        fmt["other"] = _noun_phrase(ccm, others[0])
        return _pick(ccm, "rem+", _REMEMBER_WITH_T).format(**fmt)
    return _pick(ccm, "rem", _REMEMBER_T).format(**fmt)


_ABOUT_ME_BOND = ["You're my friend. I trust you.", "We go way back. You know I count on you."]
_ABOUT_ME_BOND_MIXED = ["You're my friend, even when things go wrong around you.",
                        "Bad things happen around us, but I still count on you."]


def _is_bond(ccm, user):
    """True if `user` is the character's seeded friend or one of its company/security anchors
    (the questionnaire's "friend" / "valued bond"). Threat events are negative by construction, so
    without this a real friend would only ever be remembered through the scary scenes."""
    try:
        import motors.core_identity as core_identity
        rule = core_identity.CORE_RULES.get("custom_friend") or {}
        if user in [c.lower() for c in rule.get("concepts", []) if isinstance(c, str)]:
            return True
    except Exception:
        pass
    anchors = getattr(getattr(ccm, "identity_anchor_system", None), "anchors", []) or []
    return any(a.get("concept", "").lower() == user and a.get("target_stat") in ("company", "security")
               for a in anchors)


def _about_user(ccm):
    user = present_name(ccm) or "user"
    events = [(t, e) for t, e in _all_events(ccm) if user in e.get("concepts", [])]
    bond = _is_bond(ccm, user)
    if not events:
        if bond:
            return _pick(ccm, "meB", _ABOUT_ME_BOND), {"found": True, "events": 0, "bond": True}
        return _pick(ccm, "me0", _ABOUT_ME_NONE), {"found": False, "events": 0}
    pos = sum(1 for _, e in events if e.get("valence") == "positive")
    neg = sum(1 for _, e in events if e.get("valence") == "negative")
    strong = any(_is_strong(e) for _, e in events)
    if bond and neg >= pos:
        return _pick(ccm, "meBM", _ABOUT_ME_BOND_MIXED if neg else _ABOUT_ME_BOND), \
            {"found": True, "events": len(events), "positive": pos, "negative": neg, "bond": True}
    if pos > neg:
        opts = _ABOUT_ME_POS_STRONG if strong and neg == 0 else _ABOUT_ME_POS
    elif neg > pos:
        opts = _ABOUT_ME_NEG_STRONG if strong and pos == 0 else _ABOUT_ME_NEG
    else:
        opts = _ABOUT_ME_MIXED
    return _pick(ccm, "me", opts), {"found": True, "events": len(events), "positive": pos, "negative": neg}


# ── 4. PUBLIC ENTRY POINT ────────────────────────────────────────────────────

# ── 4. "WHERE ARE WE GOING?" — answered from what was said this scene ────────
# The window keeps, per turn, who spoke and the concepts (action + subject). A "where" question about a
# motion verb looks for the latest earlier turn that had a motion verb and answers with the place that
# came with it. Closed templates, draft wording to review. If nothing was said, it says so (it never
# accepts "that" as an answer to a question).
_WHERE = re.compile(r"\bwhere\b", re.I)
# 2026-09-26 (author's report): only the gerund/participle forms were listed here, so a turn
# phrased with the bare verb ("You want to GO to the market?", "let's HEAD to the market")
# never counted as a motion turn at all -- resolve_concept("go") returns the concept "go"
# itself, not "going" (concepts aren't lemmatized to a canonical tense), so `turn["concepts"]`
# held "go", which this set didn't recognize, and _answer_where's backward scan skipped that
# turn outright even though it's exactly the one that named the destination.
_MOTION = {"go", "going", "head", "heading", "headed", "walk", "walking",
           "travel", "traveling", "march", "marching"}
_WHERE_FOUND_T = ["To {np}.", "We're headed to {np}.", "{Np}. That's where we're going.",
                  "{Np}, like you said."]
_WHERE_UNKNOWN_T = ["I don't know. You tell me.", "No idea. Where to?", "You haven't said."]


def _turns_before_now(ccm):
    """Every turn record still held (window + short term), newest first, without the current cycle."""
    mem = ccm.memory_m
    by_cycle = {}
    for t in list(mem.window_turns(before_cycle=mem._cycle)):
        by_cycle[t["cycle"]] = t
    for e in mem.short_term:
        for t in e.get("turns", []):
            if t["cycle"] < mem._cycle:
                by_cycle.setdefault(t["cycle"], t)
    return [by_cycle[c] for c in sorted(by_cycle, reverse=True)]


def _place_score(concept):
    from db.db_concepts import CONCEPTS
    try:
        from db.db_lexicon import LEXICON
        cat = LEXICON.get(concept, {}).get("category")
    except Exception:
        cat = None
    sub = CONCEPTS.get(concept, {}).get("subtype")
    return 2 if (cat == "place" or sub in ("place", "building", "landform")) else 1


def _destination(ccm, turn):
    """The concept of a turn that says WHERE (a place first, any other content noun otherwise)."""
    from db.db_concepts import CONCEPTS
    me = (ccm.character_name or "").lower()
    skip = _QUESTION_WORDS | _MOTION | {me, turn.get("speaker")}
    # 2026-09-26 (author's report): "quality" (adjective) concepts were missing from this
    # exclusion -- an emotion tag pooled into the turn's concepts (core/memory_claims.py's
    # matching _NON_SUBJECT_TYPES already excludes these for the same reason: "I don't
    # remember the eat" is never said, and neither is "we're headed to the happy") could
    # tie a real place/thing on _place_score and win the tie-break by coming first in the
    # turn's concept list -- e.g. an emotion tag set on the SAME turn as "we're going to the
    # market" ("Happy" -> concept "happy", pooled in before "market" is even reached, see
    # cycle_manager_v5.py's pooled_text) made a LATER "Where are we going?" answer
    # "To the happy." instead of "To the market.".
    cands = [c for c in turn["concepts"]
             if c not in skip and CONCEPTS.get(c, {}).get("type") not in ("language", "action", "quality")]
    if not cands:
        return None
    return max(cands, key=lambda c: (_place_score(c), -cands.index(c)))


def _answer_where(ccm, raw_text, concepts):
    if not _WHERE.search(raw_text) or not (set(concepts) & _MOTION):
        return None
    for turn in _turns_before_now(ccm):                    # newest first
        if not (set(turn["concepts"]) & _MOTION):
            continue
        dest = _destination(ccm, turn)
        if dest:
            np_ = _noun_phrase(ccm, dest)
            return {"phrase": _pick(ccm, "where", _WHERE_FOUND_T).format(np=np_, Np=_cap(np_)),
                    "subject": dest, "kind": "where", "found": True, "tier": "context",
                    "action": f"thinking about {np_}"}
    return {"phrase": _pick(ccm, "where0", _WHERE_UNKNOWN_T), "subject": None, "kind": "where",
            "found": False, "action": "wondering where we are headed"}


def build_recall(ccm, raw_text: str, concepts: list):
    """
    Returns None if the text is not a recall question; otherwise
      {"phrase": str, "subject": str|None, "kind": str, "found": bool, "action": str}
    `action` is the gerund line for the <<...>> fragment ("recalling the monster").
    """
    q = detect_recall_query(raw_text)
    if not q:
        return _answer_where(ccm, raw_text, concepts)

    if q["kind"] == "about_me":
        phrase, info = _about_user(ccm)
        return {"phrase": phrase, "subject": present_name(ccm) or "user",
                "kind": "about_me", "found": info["found"], "action": "thinking about you", **info}

    # kind == "remember": which concepts is the question about?
    time_words = _time_words(raw_text)
    content = [c for c in _content_concepts(ccm, concepts) if c not in time_words]
    universe = set()
    for _, e in _all_events(ccm):
        universe.update(_ev_concepts(e))
    # words the tokenizer/lexicon didn't resolve (names) but memory knows
    for tok in _tokens(raw_text):
        if tok in universe and tok not in content and tok not in _QUESTION_WORDS and tok not in time_words:
            content.append(tok)
    remembered_content = [c for c in content if c in universe]

    time_bucket = q["time"]
    if content and not remembered_content:
        np_ = _noun_phrase(ccm, content[0])
        return {"phrase": _pick(ccm, "no1", _NOTHING_ABOUT_T).format(np=np_, Np=_cap(np_)),
                "subject": content[0], "kind": "subject", "found": False,
                "action": f"trying to remember {np_}"}

    matches = find_events(ccm, remembered_content, time_bucket)
    if not matches:
        text = _pick(ccm, "no2", _NOTHING_TIME_T if time_bucket else _NOTHING_AT_ALL_T)
        return {"phrase": text, "subject": None, "kind": "time" if time_bucket else "any",
                "found": False, "action": "trying to remember"}

    tier, event = matches[0]
    user = present_name(ccm)
    if remembered_content:
        subject = next((c for c in remembered_content if c in _ev_concepts(event)), remembered_content[0])
    else:
        subject = next((c for c in event.get("concepts", []) if c != user and c not in _QUESTION_WORDS),
                       (event.get("concepts") or ["that"])[0])
    return {"phrase": _describe(ccm, tier, event, subject), "subject": subject,
            "kind": "subject" if remembered_content else ("time" if time_bucket else "any"),
            "found": True, "tier": tier, "action": f"remembering {_noun_phrase(ccm, subject)}"}
