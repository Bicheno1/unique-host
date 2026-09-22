# character/valence.py — UNIQUE HOST
#
# Accumulated Valence — the general -> specific -> free-text-memory
# refinement chain (ESTADO_DEL_fullsystem.md +).
#
# the mechanism is a WEIGHTED AVERAGE, not a raw
# add/subtract delta ("adds or subtracts on top of what is inherited", 's original
# wording) and not a plain 50/50 average. Each more specific layer
# REFINES the one below it -- pulls the value toward itself, but never
# fully overwrites it. This matters because plans an unlimited
# free-text-memory layer on top of the questionnaire layers; a raw
# replace ("the most specific one wins", 's original wording) would let
# one passing mention in a memory erase a deliberate questionnaire
# answer. A weighted average can't do that -- the parent layer always
# keeps some pull.
#
#   final = (1 - w) * general + w * specific
#
# Algebraically identical to "add/subtract the full delta", since
# general + w*(specific - general) == (1-w)*general + w*specific --
# they were never two different mechanisms, just two ways of writing
# the same formula. What actually distinguishes the 3 options discussed:
#   w = 1.0  -> specific fully replaces general ("the most specific one wins")
#   w = 0.5  -> plain average, both layers pulled equally
#   w = 0.7  -> CONFIRMED: specific dominates, general still pulls a bit
#
# w=0.7 for BOTH transitions (general->specific, specific->free-text
# memory) -- confirmed. Revisit if a future
# layer turns out to need a different weight (e.g. a single offhand
# memory mention arguably should weigh less than a deliberate
# questionnaire answer -- not raised yet, so left at 0.7 for now).
#
# Scale: 1-10 (matches every questionnaire slider in
# character/questionnaire.py). A weighted average of two values already
# inside [1,10] can never leave that range, so no clamping is needed --
# this resolves 's "clamp or free?" open question FOR THIS FORMULA
# specifically (doesn't apply to raw-delta approaches, which do need one).

DEFAULT_WEIGHT = 0.7


def refine_valence(general: float, specific: float, w: float = DEFAULT_WEIGHT) -> float:
    """
    Blends a more general valence (e.g. family_opinion = 8) with a more
    specific one (e.g. opinion of one particular parent = 5) into a
    single refined value.

    w is how much the SPECIFIC value dominates:
      w=1.0 -> full replacement (specific wins outright)
      w=0.5 -> plain average
      w=0.0 -> specific value ignored entirely
    Confirmed default: 0.7 (specific dominates, general still pulls).

    Example (confirmed with the author): refine_valence(8, 5) == 5.9
    """
    general  = float(general)
    specific = float(specific)
    w = max(0.0, min(1.0, float(w)))
    return (1.0 - w) * general + w * specific


def refine_chain(values: list, w: float = DEFAULT_WEIGHT) -> float:
    """
    Applies refine_valence() left-to-right across a list of values
    ordered from most general to most specific, e.g.:

        refine_chain([family_opinion, dad_opinion, memory_derived_value])

    Each step refines the running result with the next, more specific
    value, using the SAME w for every transition (confirmed 2026-09-05).
    Needs at least one value.
    """
    if not values:
        raise ValueError("refine_chain() needs at least one value")
    result = float(values[0])
    for v in values[1:]:
        result = refine_valence(result, v, w)
    return result


# ── CONCEPT PUSH — mapping a single 1-10 concept value to all 4 axes ────
#
# Confirmed, for any concept the character rates 1-10
# (family_opinion, animals_opinion, core_fear, core_comfort, and any
# future world/likes-tree leaf):
#
#   Norte/Sur (V/P, I/A)   -> UNIVERSAL: the raw value and its complement
#                             (10 - value). Same for every character --
#                             Fortitude's own influence already happens
#                             later, when apply_external combines this
#                             push with the character's base.
#
#   East/West (Lv/Er, Gv/Rr) -> NOT universal: it's not just "how much",
#                             it's "which side" -- and that depends on
#                             whether THIS character leans empathetic
#                             (high Gv/Rr) or self-centered/ego-driven
#                             (high Lv/Er). Resolved by refine_valence
#                             between the character's own Fortitude for
#                             that axis (general layer) and the
#                             concept's value (specific layer) --
#                             reusing the exact same mechanism as the
#                             general->specific concept refinement above,
#                             no separate rule needed.
#
# 9/Lv=4.5 (leans Gv); an
# ego-driven character (fort_Gv=1, fort_Lv=9) gets Gv=4.5/Lv=6.9 (leans
# Lv) -- same input value, personality decides the direction.
#
# Scale: fortitude values and concept values both come in on 1-10 (raw
# questionnaire scale) and get converted to the engines' functional
# 0-50 range via the SAME linear scale as Fortitude itself
# (character/questionnaire.py:_fortitude_scale).

FORTITUDE_TARGET_RANGE = 50.0


def _scale_1_10_to_50(value_1_10: float) -> float:
    return (float(value_1_10) / 10.0) * FORTITUDE_TARGET_RANGE


def compute_concept_push(fortitude: dict, value_1_10: float, biological: bool, w: float = DEFAULT_WEIGHT) -> dict:
    """
    Maps a single 1-10 concept rating (e.g. family_opinion=8) to a full
    somatic + mental push vector, personalized by the character's own
    Fortitude.

    `biological` (confirmed 2026-09-05, see §23 of the state doc) gates
    WHICH side of the East/West pair gets pulled by the concept's value:
    a biological/subject concept (family, animal, a person) pulls Gv/Rr
    (empathy) -- matches the existing hardcoded "attachment" profile in
    db_somatic.py's concept_person (Lv=8 low, Gv=22 high, NOT a parallel
    blend of both). A non-biological/object concept (coffee, a chair)
    pulls Lv/Er (ego/self-reference) instead. The side NOT selected stays
    at the character's own Fortitude baseline, unmodified by this
    concept's value -- it isn't "the concept's business".

    `fortitude` must have the character's 1-10 raw Fortitude answers for
    at least fort_Gv, fort_Lv, fort_Rr, fort_Er (fort_V/fort_P aren't
    needed here -- V/P/I/A don't blend with Fortitude at this stage).

    Returns {"somatic": {V,I,Lv,Gv}, "mental": {P,A,Er,Rr}}, all already
    scaled to the 0-50 functional range.
    """
    value = float(value_1_10)
    complement = 10.0 - value

    if biological:
        gv = refine_valence(fortitude["fort_Gv"], value, w)
        lv = fortitude["fort_Lv"]          # neutral floor: character's own baseline, ungated
        rr = refine_valence(fortitude["fort_Rr"], value, w)
        er = fortitude["fort_Er"]
    else:
        lv = refine_valence(fortitude["fort_Lv"], value, w)
        gv = fortitude["fort_Gv"]          # neutral floor: character's own baseline, ungated
        er = refine_valence(fortitude["fort_Er"], value, w)
        rr = fortitude["fort_Rr"]

    somatic = {
        "V":  _scale_1_10_to_50(value),
        "I":  _scale_1_10_to_50(complement),
        "Gv": _scale_1_10_to_50(gv),
        "Lv": _scale_1_10_to_50(lv),
    }
    mental = {
        "P":  _scale_1_10_to_50(value),
        "A":  _scale_1_10_to_50(complement),
        "Rr": _scale_1_10_to_50(rr),
        "Er": _scale_1_10_to_50(er),
    }
    return {"somatic": somatic, "mental": mental}
