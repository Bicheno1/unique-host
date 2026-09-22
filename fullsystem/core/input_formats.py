# core/input_formats.py — UNIQUE HOST placeholder
#
# INPUT FORMAT MATCHER (card-style)
# ══════════════════════════════════════════════════════════════
# UNIQUE HOST does not parse free-form grammar. Incoming messages are
# split by the Marker Parser into up to three fragments:
#
#     "emotion"   -> quoted text, e.g.  "Enfadada"
#     "dialogue"  -> plain text,  e.g.  Callate
#     "action"    -> double-angle text, e.g. <<Marchandose>>
#
# Each *named format* below is one "card": a known input pattern that
# the design has already defined by hand. This file is only
# a PLACEHOLDER skeleton — the actual matching rules, activation
# conditions per quadrant, and true card names/effects will be supplied
# later and are NOT to be inferred or guessed here.
#
# Every format entry declares:
#   required_markers: which of {"emotion","dialogue","action"} must be
#                       present for this card to be considered a match
#   quadrant_gate: optional — restrict this card to a specific
#                       mental/somatic quadrant (None = any quadrant)
#   response_format: name of the output card (from output/phrase_builder
#                       FORMATS, or a future output format table) that
#                       UNIQUE HOST plays back when this card is matched
#   note: short placeholder description (English)

INPUT_FORMATS = {

    "ATTACK": {
        "required_markers": ["action"],
        "quadrant_gate":    None,
        "response_format":  "DEFENSE",
        "note": "Placeholder — user plays an aggressive/forceful action card.",
    },

    "DEFENSE": {
        "required_markers": ["action"],
        "quadrant_gate":    None,
        "response_format":  "COUNTER",
        "note": "Placeholder — user plays a guarding/protective action card.",
    },

    "EVALUATION": {
        "required_markers": ["dialogue"],
        "quadrant_gate":    None,
        "response_format":  "APPRAISAL",
        "note": "Placeholder — user asks/states something to be judged or assessed.",
    },

    "EMOTIONAL_OPENING": {
        "required_markers": ["emotion"],
        "quadrant_gate":    None,
        "response_format":  "MIRROR",
        "note": "Placeholder — user leads with an emotion tag alone, no action/dialogue.",
    },

    "COMBINED_APPROACH": {
        "required_markers": ["emotion", "dialogue"],
        "quadrant_gate":    None,
        "response_format":  "EMPATHIC_REPLY",
        "note": "Placeholder — emotion + dialogue together, no physical action.",
    },

    "FULL_SCENE": {
        "required_markers": ["emotion", "dialogue", "action"],
        "quadrant_gate":    None,
        "response_format":  "FULL_REACTION",
        "note": "Placeholder — all three fragments present at once (richest input).",
    },

    "SILENT_ACTION": {
        "required_markers": ["action"],
        "quadrant_gate":    None,
        "response_format":  "OBSERVE",
        "note": "Placeholder — action only, no emotion or dialogue given.",
    },

    "WITHDRAWAL": {
        "required_markers": ["action"],
        "quadrant_gate":    "absent-rational",
        "response_format":  "RETREAT",
        "note": "Placeholder — disengaging action while mental state is absent-rational.",
    },
}


def match_format(marked_input: dict, mental_quadrant: str = None) -> str | None:
    """
    Placeholder matcher — returns the name of the first INPUT_FORMATS
    entry whose required_markers are all present in marked_input and
    whose quadrant_gate (if any) matches mental_quadrant.

    TODO(unique_host): replace with the author's real card-matching
    logic once the actual format list and precedence rules are supplied.
    """
    present = {k for k, v in (marked_input or {}).items() if v}

    for name, fmt in INPUT_FORMATS.items():
        required = set(fmt["required_markers"])
        if not required.issubset(present):
            continue
        gate = fmt.get("quadrant_gate")
        if gate is not None and gate != mental_quadrant:
            continue
        return name

    return None
