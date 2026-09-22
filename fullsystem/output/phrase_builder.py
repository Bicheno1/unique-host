# output/phrase_builder.py — CCM v8
#
# Builds phrases compositionally from slots — no hardcoded strings.
#
# MAIN FLOW:
#   build_phrase()          → responds to identity questions
#   build_reactive_phrase() → reactive phrase based on quadrant + tension
#   build_contradiction_phrase() → negates logical contradictions
#
# FORMATS:
#   Each quadrant/tension defines a list of slots.
#   resolve_slot() resolves each slot from active_concepts + core + memory.
#   No complete phrase is stored anywhere.

from db.db_concepts import CONCEPTS

# reuses the EXISTING 16-verb mode system (RESPONSE_MATRIX
# in core/response_matrix.py) as the single source of truth for whether
# Delia is calm/open enough to share PERSONAL info (father, pet -- not
# her own name, which is already gated separately by _host_distressed
# in cycle_manager_v5.py, same as before). No new decision logic here:
# just reads whichever mode the matrix already picked this cycle.
_TRUST_MODES = {"accept", "cooperate", "observe", "signal", "group"}
_ALWAYS_SHAREABLE_PROPERTIES = {"name"}

MENTAL_RESPOND_THRESHOLD = 90.0

# ── FORMATS ───────────────────────────────────────────────────────────────────
# Slot lists per (quadrant, tension).
# Available slots: subject_internal, subject_external, focus, verb,
#                    property, value, negation, exclamation

FORMATS = {
    "present-emotional": {
        "low":      ["subject_internal", "verb", "focus"],
        "medium":   ["subject_internal", "verb", "focus"],
        "high":     ["verb", "focus"],
        "critical": ["exclamation"],
    },
    "present-rational": {
        "low":      ["subject_internal", "verb", "focus"],
        "medium":   ["subject_internal", "property", "verb", "focus"],
        "high":     ["property", "verb", "focus"],
        "critical": ["subject_internal", "property", "verb", "focus"],
    },
    "absent-emotional": {
        "low":      ["subject_internal", "emotion_state", "focus"],
        "medium":   ["subject_internal", "emotion_state", "focus"],
        "high":     ["emotion_state", "focus"],
        "critical": ["exclamation"],
    },
    "absent-rational": {
        "low":      ["subject_internal", "negation", "verb", "focus"],
        "medium":   ["negation", "focus"],
        "high":     ["negation"],
        "critical": [],   # no verbal — somatic takes control
    },
}

# ── SLOT RESOLVER ─────────────────────────────────────────────────────────────

def resolve_slot(slot, active_concepts, core_rules, focus=None, memory_value=None,
                 quadrant=None, valence=None, emotion=None):
    """Resolves a slot → word/string."""

    if slot == "subject_internal":
        return "I"

    if slot == "subject_external":
        return "you"

    if slot == "focus":
        if focus:
            # Use the concept key as display label — synonyms are for input resolution only
            return focus
        return ""

    if slot == "property":
        for name in active_concepts:
            c = CONCEPTS.get(name, {})
            if c.get("subtype") == "property":
                return name
        return ""  # no property in scene — skip this slot

    if slot == "verb_ser":
        return "am"

    if slot == "verb":
        # state/being verb based on quadrant
        if quadrant and "absent" in quadrant:
            return "feel"
        return "sense"

    if slot == "value":
        # Fix: this had its OWN hardcoded.get("name", "")
        # lookup here, completely ignoring the `memory_value` param --
        # so even though build_phrase correctly figured out "Thomas"
        # was the right answer for "who is your father" and passed it
        # in as memory_value, THIS is where the final word actually
        # gets produced, and it silently threw that away and returned
        # "Delia" (the "name" field) every time, because it checked the
        # core_rules identity dict first and returned unconditionally
        # before ever looking at memory_value. Two identity-value
        # lookups existed (this one, and _get_identity_value above)
        # and only one of them knew about property_name -- now the
        # already-correct value takes priority, falling back to the old
        # "name" default only when nothing more specific was resolved.
        if memory_value:
            return memory_value
        for _, rule in (core_rules or []):
            if rule.get("type") == "identity":
                return rule.get("value", {}).get("name", "")
        return ""

    if slot == "action":
        # direct action — comes as memory_value (already resolved externally)
        return memory_value or ""

    if slot == "negation":
        return "not"

    if slot == "exclamation":
        if valence == "positive":
            return "Yes!"
        return "No!"

    if slot == "emotion_state":
        return emotion or "feel"

    return ""


# ── HELPERS ───────────────────────────────────────────────────────────────────

def can_respond(dist_mental: float) -> bool:
    return dist_mental < MENTAL_RESPOND_THRESHOLD

def is_opening(dist_mental: float) -> bool:
    return dist_mental < 20.0

def _get_focus(active_concepts: list) -> str | None:
    """Returns the concept with the highest semantic weight (non-language)."""
    content = [c for c in active_concepts
               if CONCEPTS.get(c, {}).get("type", "") != "language"]
    return content[0] if content else None

def _threat_active(core_rules: list) -> bool:
    return any(rule.get("effect") == "guard_identity"
               for _, rule in (core_rules or []))

# open, growable set of properties the identity system can
# actually answer about -- mirrors whichever "property"-subtype
# concepts exist in db_concepts.py. Add a new name here (and a matching
# key in the character's host_identity.value dict) any time a new
# property concept is added.
_KNOWN_IDENTITY_PROPERTIES = {"name", "father", "mother", "pet"}

def _get_identity_value(core_rules: list, memory_value: str = None,
                         property_name: str = "name") -> str:
    """
    2026-09-09: was hardcoded to always read .get("value", {}).get("name"
    ...) no matter WHICH property was actually asked about -- fine while
    "name" was the only property concept that existed, but silently
    wrong the moment more are added (asking about "father" would have
    quietly returned Delia's own name instead). Now looks up whichever
    property_name detect_pattern() actually found; a rule that doesn't
    have that key returns "" (a real "don't know"/no data) rather than
    falling back to name.
    """
    for _, rule in (core_rules or []):
        if rule.get("type") == "identity":
            return rule.get("value", {}).get(property_name, "")
    return memory_value or ""

def _identity_sentence(lookup_key, value, active_concepts, core_rules, dist_mental):
    """Reads a property back as a real sentence: 'I am Mira' for the name,
    'My father is Teodor' for the relations (was 'I am Teodor')."""
    if lookup_key in ("father", "mother", "pet"):
        return f"My {lookup_key} is {value}"
    fmt = ["subject_internal", "verb_ser", "value"] if dist_mental < 50 else ["value"]
    return build_from_format(fmt, active_concepts, core_rules,
                             memory_value=value, quadrant="present-rational")


def detect_pattern(active_concepts: list) -> dict:
    pattern = {
        "type":            None,
        "has_interrogant": False,
        "has_verb":        False,
        "has_property":    False,
        "has_subject_ext": False,
        "has_subject_int": False,
        "property_name":   None,
        "has_content":     False,   # a non-grammar concept is present ("afraid", "old"...)
    }
    # Fix: a sentence
    # like this legitimately contains TWO property concepts at once
    # ("father" AND "name" -- it's asking for the father's name, not
    # Delia's). This used to just overwrite property_name on every
    # property concept found, so whichever came LAST in active_concepts
    # won arbitrarily -- "name" is the generic identity property and
    # will show up any time someone asks "what's X's NAME", silently
    # stomping the actually-specific one ("father"/"mother"/"pet")
    # every single time both appear together, which is the normal case
    # for this exact phrasing. Now collects every property concept
    # found and prefers a SPECIFIC one (anything other than the generic
    # "name"/"identity") when both kinds are present.
    property_names_found = []
    for name in active_concepts:
        c       = CONCEPTS.get(name, {})
        subtype = c.get("subtype", "")
        if c.get("type") != "language":
            if c: pattern["has_content"] = True
            continue
        if subtype == "question_word": pattern["has_interrogant"] = True
        elif subtype == "verb":        pattern["has_verb"] = True
        elif subtype == "property":
            pattern["has_property"] = True
            property_names_found.append(name)
        elif subtype == "external_subject": pattern["has_subject_ext"] = True
        elif subtype == "internal_subject": pattern["has_subject_int"] = True

    if property_names_found:
        specific = [p for p in property_names_found if p not in ("name", "identity")]
        pattern["property_name"] = specific[0] if specific else property_names_found[-1]

    if pattern["has_interrogant"]:
        pattern["type"] = "question"
    elif pattern["has_verb"] or pattern["has_property"]:
        pattern["type"] = "statement"
    return pattern


# ── BUILD FROM FORMAT ─────────────────────────────────────────────────────────

def build_from_format(fmt, active_concepts, core_rules, focus=None,
                      memory_value=None, quadrant=None, valence=None, emotion=None):
    """
    Fills a list of slots and returns the composed phrase.
    Returns None if the format is empty or all slots are empty.
    """
    if not fmt:
        return None
    parts = []
    for slot in fmt:
        word = resolve_slot(slot, active_concepts, core_rules, focus=focus,
                            memory_value=memory_value, quadrant=quadrant,
                            valence=valence, emotion=emotion)
        if word:
            parts.append(word)
    if not parts:
        return None
    phrase = " ".join(parts)
    return phrase[0].upper() + phrase[1:]


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def build_phrase(active_concepts: list, core_rules: list,
                 dist_mental: float, memory_value: str = None,
                 current_mode: str = None) -> str | None:
    """
    Responds to identity questions if the host can respond.
    Uses FORMATS["present-rational"] with identity slots.

    current_mode (2026-09-09): the verb select_axis_response() already
    picked this cycle from RESPONSE_MATRIX (one of the 16 modes --
    attack/flee/suppress/... vs accept/cooperate/observe/...). Deciding
    whether to share something PERSONAL (father, pet) reuses this
    directly instead of inventing a separate willingness check: the
    matrix's own trusting-vs-defensive modes already ARE that decision
    for this cycle, so a defensive mode (mid-fight, suppressing a
    threat) means personal facts don't come out, same instinct as not
    pausing a fight to talk about your dad. Her own name stays always
    answerable (_ALWAYS_SHAREABLE_PROPERTIES) -- that's a much lower bar
    than family/pets and was already covered by the coarser
    _host_distressed gate in cycle_manager_v5.py before this existed.
    """
    if not can_respond(dist_mental):
        return None

    pattern = detect_pattern(active_concepts)

    if pattern["type"] == "question":
        if _threat_active(core_rules):
            return "I won't tell you!"
        # Fix: # detect_pattern already requires has_interrogant=True for
        # pattern["type"] to BE "question" at all (see its own body --
        # "if has_interrogant: type=question"). So the OLD third
        # alternative here, "or pattern['has_interrogant']", was always
        # true the moment this branch is even reached -- structurally a
        # no-op condition that made EVERY question (any sentence
        # containing "what"/"who"/"where"/etc. ANYWHERE, not necessarily
        # about identity) fall through to answer "I am Delia". Confirmed:
        # "maybe we should just give him what he wants" (the "what" is
        # inside "what he wants", nothing to do with Delia's name)
        # produced "I am Delia" out of nowhere.
        # A real identity question needs the interrogative word to
        # actually be ABOUT identity/name (has_property name/identity)
        # OR about "you" specifically (has_subject_ext -- "who are
        # you?" has no property word but does point the question at the
        # character). Interrogant alone is no longer sufficient.
        #
        # generalized past just "name" -- _KNOWN_IDENTITY_PROPERTIES
        # is an open, growable set (mirrors the new "father"/"pet"
        # concepts in db_concepts.py). Whichever one was actually asked
        # about gets looked up specifically; a bare "who are you" (no
        # property word, just has_subject_ext) still defaults to "name".
        _property_key = "name" if pattern["property_name"] == "identity" else pattern["property_name"]
        _asks_identity = pattern["has_property"] and _property_key in _KNOWN_IDENTITY_PROPERTIES
        # Note: "or pattern['has_subject_ext']" used to fire
        # on ANY question containing "you", even when a property WAS
        # detected and it just wasn't an identity one (e.g. "afraid" in
        # "What are you afraid of, Delia?") -- _asks_identity came back
        # False for that case, but has_subject_ext was still True, so it
        # fell through to lookup_key="name" and answered "I am Delia" to
        # an unrelated question. A bare "who are you?" (has_subject_ext
        # with NO property detected at all) should still default to
        # name -- that's the genuine generic case -- but a question with
        # a real, just-unrecognized property should fall through to
        # `return None` below and let the matrix answer instead.
        # a bare "who are you?" defaults to the name only when the
        # question holds NO other content concept ("What are you afraid of?",
        # "How old are you?" carry one and must go to the matrix instead).
        if _asks_identity or (pattern["has_subject_ext"] and not pattern["has_property"]
                              and not pattern["has_content"]):
            lookup_key = _property_key if _asks_identity else "name"
            if lookup_key not in _ALWAYS_SHAREABLE_PROPERTIES and current_mode not in _TRUST_MODES:
                return None  # not in a trusting-enough mode to share this right now
            value = _get_identity_value(core_rules, memory_value, property_name=lookup_key)
            if value:
                return _identity_sentence(lookup_key, value, active_concepts, core_rules, dist_mental)

    if (pattern["type"] == "statement"
            and pattern["has_subject_ext"]
            and pattern["has_property"]
            and (pattern["property_name"] in _KNOWN_IDENTITY_PROPERTIES
                 or pattern["property_name"] == "identity")):
        if _threat_active(core_rules):
            return "I won't tell you!"
        _stmt_property_key = "name" if pattern["property_name"] == "identity" else pattern["property_name"]
        if _stmt_property_key not in _ALWAYS_SHAREABLE_PROPERTIES and current_mode not in _TRUST_MODES:
            return None  # same trust gate as the question branch above
        value = _get_identity_value(
            core_rules, memory_value,
            property_name=_stmt_property_key,
        )
        if value:
            return _identity_sentence(_stmt_property_key, value, active_concepts, core_rules, dist_mental)

    return None


def build_reactive_phrase(active_concepts: list, cfx: float, tension: str,
                           quadrant: str, dist_mental: float,
                           emotion: str = None) -> str | None:
    """
    Reactive phrase based on quadrant + tension.
    Selects the format from FORMATS and fills it with resolve_slot.
    """
    if not can_respond(dist_mental):
        return None

    from layers.processing_mode import get_processing_mode

    pm      = get_processing_mode(cfx, tension)
    focus   = _get_focus(active_concepts)
    valence = "positive" if "present" in quadrant else "negative"

    if pm["preverbal"]:
        return None

    fmt = FORMATS.get(quadrant, {}).get(tension)
    return build_from_format(fmt, active_concepts, core_rules=[], focus=focus,
                              quadrant=quadrant, valence=valence, emotion=emotion)


def build_contradiction_phrase(contradiction_info: dict, dist_mental: float) -> str | None:
    """
    Negates logical contradictions (e.g.: "fish don't fly").
    """
    if not contradiction_info.get("is_contradiction"):
        return None
    if dist_mental >= 90:
        return None

    # identity contradictions (paper dual-check, see
    # core/pre_input.py:detect_identity_contradiction) get their own
    # phrasing -- "I am <real value>" -- not the "you not X Y" negation
    # template built below for (subject, action) scene contradictions.
    # contradiction with a STORED MEMORY (core/memory_claims.py) -- the phrase
    # ("That's not how it was. The monster a while back... It felt good.") is already built.
    if contradiction_info.get("contradiction_type") == "memory":
        return contradiction_info.get("phrase")

    if contradiction_info.get("contradiction_type") == "identity":
        real_value = contradiction_info.get("real_value")
        if real_value is None:
            return None
        prop = contradiction_info.get("property")
        value_str = f"{real_value} years old" if prop == "age" else str(real_value)
        return build_from_format(["subject_internal", "verb_ser", "value"],
                                  active_concepts=[], core_rules=[],
                                  memory_value=value_str, quadrant=None)

    subj = contradiction_info.get("subject_label", "that")
    act  = contradiction_info.get("action_label",  "do that")

    # this used to build "You not fly cow" (loose slots:
    # subject_external + negation + action + focus). Now full sentences
    # (core/response_bank.py explains the same problem in the mode
    # templates). If the real subject or action is missing, it falls back to a generic sentence.
    if subj in (None, "", "that") or act in (None, "", "do that"):
        return "That's not right."
    return _contradiction_sentence(subj, act, short=(dist_mental >= 50))


def _with_article(noun: str) -> str:
    """'cow' -> 'a cow', 'owl' -> 'an owl'; respects an article that is already present."""
    first = noun.split(" ", 1)[0].lower()
    if first in ("a", "an", "the", "his", "her", "their", "my", "your", "our"):
        return noun
    return ("an " if noun[:1].lower() in "aeiou" else "a ") + noun


def _gerund(action: str) -> str:
    """'fly' -> 'flying'; multi-word: only the first one is inflected."""
    from lemminflect import getInflection
    head, _, rest = action.partition(" ")
    ing = getInflection(head, tag="VBG")
    head = ing[0] if ing else head + "ing"
    return f"{head} {rest}".strip()


_CONTRADICTION_VARIANTS = [
    "Wait — {a} can't {act}.",
    "That's not right. {a_cap} doesn't {act}.",
    "{a_cap} {ger}? That can't be right.",
    "{a_cap} {ger}? No. That's not how it works.",
]
_CONTRADICTION_SHORT = [
    "No. {a_cap} can't {act}.",
    "{a_cap} {ger}? No.",
]


def _contradiction_sentence(subj: str, act: str, short: bool = False) -> str:
    import random
    a = _with_article(subj)
    template = random.choice(_CONTRADICTION_SHORT if short else _CONTRADICTION_VARIANTS)
    return template.format(a=a, a_cap=a[:1].upper() + a[1:], act=act, ger=_gerund(act))
