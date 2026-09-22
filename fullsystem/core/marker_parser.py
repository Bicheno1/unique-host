# core/marker_parser.py — UNIQUE HOST
#
# MARKER PARSER
# ═══════════════════════════════════════════════════
# Splits a raw roleplay message into its three recognized fragments:
#
#   "..."      -> emotion   (e.g.  "Angry")
#   <<...>>    -> action    (e.g.  <<Storming off>>)
#   plain text -> dialogue  (whatever is left over)
#
# Example:
#   '"Angry" Shut up <<Storming off>>'
#   -> {"emotion": "Angry", "dialogue": "Shut up", "action": "Storming off"}
#
# TODO: confirm edge cases (multiple emotion tags, emotion
# appearing mid-message, nested markers) once the real Format list is
# supplied — this is a straightforward regex placeholder for now.

import re

_ACTION_RE  = re.compile(r"<<(.*?)>>")
_EMOTION_RE = re.compile(r'"([^"]*)"')


def parse_marked_input(text: str) -> dict:
    """Returns {"emotion": str|None, "dialogue": str|None, "action": str|None}."""
    if not text:
        return {"emotion": None, "dialogue": None, "action": None}

    remaining = text

    action_match = _ACTION_RE.search(remaining)
    action = action_match.group(1).strip() if action_match else None
    remaining = _ACTION_RE.sub("", remaining)

    emotion_match = _EMOTION_RE.search(remaining)
    emotion = emotion_match.group(1).strip() if emotion_match else None
    remaining = _EMOTION_RE.sub("", remaining)

    dialogue = remaining.strip() or None

    return {"emotion": emotion, "dialogue": dialogue, "action": action}


def format_marked_output(emotion: str = None, dialogue: str = None,
                          action: str = None) -> str:
    """
    The output-side mirror of parse_marked_input() -- builds a response
    in the SAME marker syntax the input side uses, so the system's real
    contract is genuinely symmetric ("in like this, out like this", per
    the system-state notes §3): '"emotion" dialogue <<action>>'.
    Any missing fragment is simply omitted (no empty "" / <<>> litter).
    Round-trips through parse_marked_input() by construction.
    """
    parts = []
    if emotion:
        parts.append(f'"{emotion}"')
    if dialogue:
        parts.append(dialogue)
    if action:
        parts.append(f"<<{action}>>")
    return " ".join(parts)
