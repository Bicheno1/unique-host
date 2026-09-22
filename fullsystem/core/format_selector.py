# core/format_selector.py — UNIQUE HOST
#
# FORMAT SELECTOR — card-style, per-quadrant, shared across engines
# ══════════════════════════════════════════════════════════════
# There are only 4 generic geometric directions — northwest (cx<0,cy>=0),
# northeast (cx>=0,cy>=0), southwest (cx<0,cy<0), southeast (cx>=0,cy<0).
# Both engines share the SAME format types/anchors for a given direction;
# only the engine-specific quadrant label maps to that direction:
#
#   mental:  present-rational  -> northwest   present-emotional -> northeast
#            absent-rational   -> southwest   absent-emotional  -> southeast
#   somatic: viable-globalized -> northwest   viable-localized  -> northeast
#            inviable-globalized -> southwest inviable-localized -> southeast
#
# Each direction holds several candidate "format types" (type1, type2...):
#   anchor: fixed (x, y) point inside that direction, hand-placed by the
#            author — the format's "home" position in the geometry
#   slots: sentence structure, e.g. ["subject", "predicate", "x"]
#   uses: how many times this type has been played so far (starts at 0,
#            increments every time it is chosen — no success/failure
#            evaluation, purely reactive like a card deck)
#
# SELECTION:
#   score(type) = proximity_weight * proximity_score(type)
#               + usage_weight     * usage_score(type)
#
#   proximity_score = 1 - (distance to anchor / max distance in direction),
#                     so closer anchors score higher (range ~0-1)
#   usage_score      = uses / (uses of most-played type in this direction),
#                     so the most-played type scores 1.0 (range 0-1)
#
# Because both engines share the same type pool per direction, `uses`
# accumulates regardless of which engine (mental/somatic) triggered the
# pick — a type played often from mental input is already "warmed up"
# if the somatic engine lands in the same direction later.
#
# TODO: FORMAT_TYPES below is a PLACEHOLDER skeleton —
# replace anchors/slots with the final values.

import math

DEFAULT_PROXIMITY_WEIGHT = 0.5
DEFAULT_USAGE_WEIGHT     = 0.5

# Max magnitude per engine (used to bound distance normalization)
MENTAL_MAX_DIST  = 100.0   # mental cx/cy max ~ MENTAL_MAX/2
SOMATIC_MAX_DIST = 200.0   # somatic cx/cy max ~ SOMATIC_MAX/2

# Maps each engine's quadrant label -> shared generic direction
QUADRANT_TO_DIRECTION = {
    # mental
    "present-rational":   "northwest",
    "present-emotional":  "northeast",
    "absent-rational":    "southwest",
    "absent-emotional":   "southeast",
    # somatic
    "viable-globalized":   "northwest",
    "viable-localized":    "northeast",
    "inviable-globalized": "southwest",
    "inviable-localized":  "southeast",
}

# Shared format types per direction — used by BOTH engines
FORMAT_TYPES = {
    "northwest": [
        {"name": "type1", "anchor": (-30.0, 40.0), "slots": ["subject", "predicate", "x"], "uses": 0},
        {"name": "type2", "anchor": (-70.0, 20.0), "slots": ["subject", "verb", "focus"],   "uses": 0},
    ],
    "northeast": [
        {"name": "type1", "anchor": (30.0, 40.0), "slots": ["subject", "verb", "focus"], "uses": 0},
        {"name": "type2", "anchor": (70.0, 20.0), "slots": ["exclamation"],               "uses": 0},
    ],
    "southwest": [
        {"name": "type1", "anchor": (-30.0, -40.0), "slots": ["subject", "negation", "focus"], "uses": 0},
        {"name": "type2", "anchor": (-70.0, -20.0), "slots": ["negation"],                       "uses": 0},
    ],
    "southeast": [
        {"name": "type1", "anchor": (30.0, -40.0), "slots": ["subject", "emotion_state", "focus"], "uses": 0},
        {"name": "type2", "anchor": (70.0, -20.0), "slots": ["exclamation"],                         "uses": 0},
    ],
}


def _distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def select_format(quadrant: str, cx: float, cy: float,
                   proximity_weight: float = DEFAULT_PROXIMITY_WEIGHT,
                   usage_weight: float = DEFAULT_USAGE_WEIGHT,
                   engine: str = "mental") -> dict | None:
    """
    Picks the best-scoring format type for the given engine-specific
    quadrant label + current (cx, cy) position. Maps the quadrant to
    its shared generic direction first, then combines proximity to
    each type's anchor with how often that type has been used before
    (by either engine). Increments the winning type's `uses` counter.
    """
    direction = QUADRANT_TO_DIRECTION.get(quadrant)
    candidates = FORMAT_TYPES.get(direction)
    if not candidates:
        return None

    max_dist = MENTAL_MAX_DIST if engine == "mental" else SOMATIC_MAX_DIST
    max_uses = max((c["uses"] for c in candidates), default=0) or 1

    best, best_score = None, -1.0
    for c in candidates:
        dist = _distance((cx, cy), c["anchor"])
        proximity_score = max(0.0, 1.0 - dist / (max_dist * math.sqrt(2)))
        usage_score = c["uses"] / max_uses

        score = proximity_weight * proximity_score + usage_weight * usage_score
        if score > best_score:
            best, best_score = c, score

    if best:
        best["uses"] += 1
    return best


def reset_usage():
    """Testing helper — clears all usage counters."""
    for candidates in FORMAT_TYPES.values():
        for c in candidates:
            c["uses"] = 0

