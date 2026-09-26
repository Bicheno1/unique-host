# core/topic_target.py — UNIQUE HOST
#
# WHO OR WHAT THE REPLY IS ABOUT: the TOPIC of what was said, not always
# the speaker.
# ══════════════════════════════════════════════════════════════
# WHY (author's report, 2026-09-23): with the "You" speaker (or any named
# speaker) the target of the reaction was pinned to the speaker for EVERY
# input (`subject = forced_focus or parsed_subject`, added 2026-09-09).
# Measured: in 137 of 144 replies to questions the core said "you", even
# when the question was about a noise or about "him" -- "What is that
# noise?" -> "We keep still and watch you."
#
# WHY IT WAS PINNED, AND WHAT THIS KEEPS: the 2026-09-09 fix (see
# construction_matcher.make_why_question docstring) made sentence and
# action line agree on ONE subject, because they used to talk about two
# different things. That still holds: both read response["subject"], which
# is decided once, here.
#
# RULE (speaker turns; narrator turns never pin a focus, so they only get
# the passive-agent and vague-noun fixes of rules 1 and 3):
#   1. Passive input -> the AGENT is the topic ("The door was broken by the
#      bandit" -> the bandit), because extract_subject() returns the
#      grammatical subject, which in a passive is the thing acted on.
#   2. Otherwise the subject extract_subject() found.
#   3. If that is empty, a pronoun, a vague noun ("the way", "the thing") or
#      the reacting character herself -> the SPEAKER, as before.
#      ("Do you know him?", "Run!", "Hello there.", "I love you.")
#
# WHAT IT DOES NOT TOUCH: who is "present" for memory, identity answers,
# and the reflective questions of `investigate` (they read forced_focus in
# select_axis_response, not the subject).

USE_TOPIC_TARGET = True   # False -> the speaker is always the target (previous behavior)

# Nouns that name nothing to react to.
_VAGUE = {
    "thing", "things", "way", "ways", "time", "times", "lot", "kind", "sort", "bit",
    "matter", "idea", "one", "ones", "case", "point", "fact", "reason", "moment",
    "part", "sense", "something", "anything", "nothing", "everything", "someone",
    "anyone", "everyone", "nobody", "somebody", "anybody", "everybody",
}
_PRONOUNS = {
    "i", "me", "my", "we", "us", "our", "you", "your", "he", "him", "his", "she",
    "her", "it", "its", "they", "them", "their", "this", "that", "these", "those",
    "there", "here", "who", "what",
}


def passive_agent(doc):
    """'The door was broken by the bandit' -> 'the bandit'. None when the
    passive has no explicit agent or the agent is a pronoun."""
    from core.construction_matcher import _add_article
    for tok in doc:
        if tok.dep_ != "agent":
            continue
        for child in tok.children:
            if child.dep_ == "pobj" and child.pos_ in ("NOUN", "PROPN"):
                proper = child.pos_ == "PROPN"
                return _add_article(child.text if proper else child.text.lower(), is_proper=proper)
    return None


def _is_valid_topic(topic: str, character_name: str = None) -> bool:
    if not topic:
        return False
    bare = topic.strip()
    if bare.lower().startswith("the "):
        bare = bare[4:]
    low = bare.lower()
    if low in _VAGUE or low in _PRONOUNS:
        return False
    if character_name and low == character_name.lower():
        return False
    return True


def pick_target(parsed: dict, forced_focus: str = None, character_name: str = None):
    """(subject, source). `source` is 'topic' (speaker turn, target taken from
    the input), 'speaker' (no clear topic, or topic targeting off), 'text'
    (narrator turn, subject parsed from the text) or 'default' (nothing
    usable -> "that").

    The passive-agent and vague-noun fixes apply to narrator turns too
    ("the door was broken by the bandit" -> "the bandit", never "the way")."""
    parsed = parsed or {}
    if forced_focus is not None and not USE_TOPIC_TARGET:
        return forced_focus, "speaker"
    topic = None
    doc = parsed.get("doc")
    if USE_TOPIC_TARGET and doc is not None and "PASSIVE_VOICE" in (parsed.get("constructions") or []):
        topic = passive_agent(doc)
    topic = topic or parsed.get("subject")
    if USE_TOPIC_TARGET and not _is_valid_topic(topic, character_name):
        topic = None
    if forced_focus is None:
        return (topic or "that"), ("text" if topic else "default")
    if topic:
        return topic, "topic"
    return forced_focus, "speaker"


def _bare_noun(subject: str) -> str:
    """Strips a leading article so the lexicon lookup sees the bare noun
    ("the market" -> "market")."""
    s = (subject or "").strip()
    low = s.lower()
    for art in ("the ", "an ", "a "):
        if low.startswith(art):
            return s[len(art):]
    return s


def is_non_biological_subject(subject: str, character_name: str = None) -> bool:
    """True only when `subject` names an OBJECT-type concept in the lexicon --
    a place, a plan, a thing ("the market", "the door", "the plan") -- as
    opposed to a SUBJECT-type one (a person, an animal, the reacting
    character herself). Pronouns, "you"/"user", the character's own name,
    and anything the lexicon doesn't resolve (most proper names among them)
    are left alone -- only a concept the lexicon positively tags
    `non_biological` counts, since guessing at an unfamiliar name is worse
    than leaving it as-is.

    2026-09-26 (author's report): the topic target correctly picked "the
    market" out of "You wanna go to the market?", but nothing then asked
    whether that topic was a PERSON or a PLACE before handing it straight
    to the templates -- "We accept the market", "thanking the market".
    """
    if not subject:
        return False
    bare = _bare_noun(subject).lower()
    if bare in _PRONOUNS or bare in ("you", "user", "i", "we"):
        return False
    if character_name and bare == character_name.lower():
        return False
    from db.db_concepts import resolve_concept, CONCEPTS
    name = resolve_concept(bare)
    if not name:
        return False
    return CONCEPTS.get(name, {}).get("type") == "object"


def to_display_subject(subject: str, character_name: str = None) -> str:
    """`subject` unchanged, or "that" when it names something
    non-biological -- "the market" -> "that" ("accepting that", not
    "accepting the market"). Gestures that need an actual person on the
    receiving end ("thanking", "smiling at"...) are handled separately,
    see core/action_bank.py's _REQUIRES_PERSON_PREFIXES."""
    if is_non_biological_subject(subject, character_name):
        return "that"
    return subject
