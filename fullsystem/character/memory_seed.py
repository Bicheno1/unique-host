# character/memory_seed.py — UNIQUE HOST
#
# PROTOTYPE —).
# Converts the "core" questionnaire answers (today: core_fear,
# core_comfort) into synthetic NUCLEAR events, with the SAME shape that
# systems/memory_system.py:MemorySystem._close_event produces live
# during play, so they can be appended directly to.long_term.
#
# WHY THIS BRIDGE EXISTS:
# The definition of "nuclear" in memory_system.py already reads, literally: "personality
# -defining events. System was in critical state AND self-regulated back to
# near-center." That is conceptually the same thing core_fear/
# core_comfort represent (pinned to the extremes of the 1-10 scale, see
# CORE_FEAR_VALUE/CORE_COMFORT_VALUE in character/questionnaire.py) — but
# today those two answers ONLY produce a static valence push
# (tag_values_seed), and never occupy the place the system itself
# already reserves for "this is defining": a nuclear entry in long_term.
#
# HOW IT IS USED:
#   events = seed_memory_from_character(character_data)   # complete character.json
#   for ev in events:
#       ccm.memory_s.long_term.append(ev)
#       ccm.memory_m.long_term.append(ev)
#
# READS THE ALREADY-BUILT character.json (core_identity_rules["custom_fear"/
# "custom_comfort"]), not the raw questionnaire answers — so it
# works the same if someone hand-edits the JSON instead of going through
# build_character_json.
#
# STATUS: prototype, NOT yet wired into character/injector.py — it is added
# on purpose as a separate step (see injector.py) so it can be tested
# in isolation before connecting it to the real flow.
#
# OPEN DECISIONS (not resolved here, left to be calibrated):
#   - _synthetic_peak is a single-pass heuristic: it maps how
#     extreme the answer was (0.0 at the midpoint 5.5, 1.0 at 1 or 10) to
#     a peak that is guaranteed to cross the nuclear threshold. It is NOT calibrated
#     against the real magnitude of events lived in a playthrough — today
#     core_fear/core_comfort are always pinned to the extremes
#     (see questionnaire.py), so in practice they ALWAYS produce
#     nuclear=True; handling of intermediate values is aspirational, in
#     case an intensity slider is added to these questions in the future.
#   - Only covers core_fear/core_comfort. If other "core" answers are
#     added to the questionnaire later, they have to be added here by hand.
#   - Reads the thresholds (HIGH_MENTAL_THRESHOLD, etc.) from the MODULE
#     systems.memory_system AT CALL TIME (it does not import them by
#     value) — so, if character/injector.py has already patched those thresholds with
#     the character's own (step 3, saturation_thresholds) BEFORE
#     seeding the memory (new step, after 3), the seeded memory
#     is calibrated against THAT character's threshold, not the global
#     default. That is why the order of the steps in injector.py matters.

import systems.memory_system as memory_system

# Must match character/questionnaire.py::CORE_FEAR_VALUE/
# CORE_COMFORT_VALUE — duplicated here on purpose to avoid creating a circular
# import (questionnaire.py does not import memory_seed.py).
CORE_FEAR_VALUE    = 1.0
CORE_COMFORT_VALUE = 10.0

# Margin over the nuclear threshold so a fully extreme value
# (1 or 10) crosses it with room to spare even after rounding. It does not come from any
# design document — it is a prototype knob, adjustable.
_NUCLEAR_MARGIN = 1.2


def _extremity(value_1_10: float) -> float:
    """0.0 at the neutral midpoint (5.5), 1.0 at either extreme (1 or 10)."""
    value_1_10 = max(1.0, min(10.0, float(value_1_10)))
    return abs(value_1_10 - 5.5) / 4.5


def _synthetic_peak(value_1_10: float) -> tuple:
    """
    Maps how extreme the answer was to a peak (D, C) — uses the
    CURRENT thresholds of the memory_system module (already patched by
    injector.py if applicable, see the file docstring). An answer
    at the midpoint (extremity=0) gives peak 0 -> _classify() returns None
    -> no memory is generated, consistent with "it was not intense enough
    to be a defining memory".
    """
    ext = _extremity(value_1_10)
    peak_D = memory_system.HIGH_SOMATIC_THRESHOLD * _NUCLEAR_MARGIN * ext
    peak_C = memory_system.HIGH_MENTAL_THRESHOLD  * _NUCLEAR_MARGIN * ext
    return peak_D, peak_C


def _build_event(word: str, value_1_10: float, label: str) -> dict:
    """
    Builds an event with the SAME shape that
    MemorySystem._close_event() produces live, so it can be appended
    directly to .long_term without the class needing to know it was seeded
    instead of lived. Returns None if it does not qualify as an event
    (insufficient peak).
    """
    peak_D, peak_C = _synthetic_peak(value_1_10)
    ec = memory_system._classify(peak_C, peak_D)
    if not ec:
        return None

    end_D = round(memory_system.BASELINE_THRESHOLD * 0.5, 4)
    end_C = round(memory_system.NUCLEAR_THRESHOLD  * 0.5, 4)

    graph = {
        "start": (0.0, 0.0),                              # before the event — calm
        "peak":  (round(peak_D, 4), round(peak_C, 4)),     # the defining moment
        "end":   (end_D, end_C),                           # self-regulated back to the center
    }

    is_nuclear = (
        (peak_C >= memory_system.HIGH_MENTAL_THRESHOLD or
         peak_D >= memory_system.HIGH_SOMATIC_THRESHOLD)
        and end_D < memory_system.BASELINE_THRESHOLD * 2
        and end_C < memory_system.NUCLEAR_THRESHOLD
    )

    return {
        "text":         f"(seeded from questionnaire — {label}: {word})",
        "concepts":     [word],
        "graph":        graph,
        "event_class":  ec,
        "is_nuclear":   is_nuclear,
        "mental_peak":  round(peak_C, 4),
        "somatic_peak": round(peak_D, 4),
        "age":          0,
        "reps":         1,
        #  (memory recall): a seeded fear is a bad memory, a seeded comfort a good one.
        "closed_at":    None,
        "valence":      "negative" if value_1_10 < 5.5 else "positive",
    }


def seed_memory_from_character(character_data: dict) -> list:
    """
    Reads character_data["core_identity_rules"]["custom_fear"/"custom_comfort"]
    (added by build_character_json() when the person answered those
    free-text questions — see character/questionnaire.py) and returns
    a list of events ready to append to .long_term.

    If the character did not answer core_fear/core_comfort, those keys do not
    exist in core_identity_rules and nothing is generated — same criterion
    the rest of the pipeline already uses (concepts_seed doesn't generate them either).
    """
    events = []
    rules = character_data.get("core_identity_rules", {})

    fear = rules.get("custom_fear")
    if fear and fear.get("concepts"):
        ev = _build_event(fear["concepts"][0], CORE_FEAR_VALUE, "core fear")
        if ev:
            events.append(ev)

    comfort = rules.get("custom_comfort")
    if comfort and comfort.get("concepts"):
        ev = _build_event(comfort["concepts"][0], CORE_COMFORT_VALUE, "core comfort")
        if ev:
            events.append(ev)

    return events
