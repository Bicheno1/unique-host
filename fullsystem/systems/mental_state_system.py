# systems/mental_state_system.py — CCM v7
#
# MENTAL STATE SYSTEM — internal complement of the mental engine.
# Exact analog of chemical_system.py but for the cognitive-emotional plane.
#
# Each "mental state" is like a chemical:
#   - Triggered by concepts entering the cycle
#   - Has a continuous circulating level (0.0 – 10.0)
#   - Generates an interpolated push {P, A, Er, Rr} based on level
#   - Decays with its own half_life
#
# DECAY:
#   decay_factor = 0.5 ^ (1 / half_life)
#   level_next   = level_current * decay_factor
#
# PUSH:
#   Given a level L, it interpolates linearly between the three points:
#     L in [0,1]   → between zero and x1
#     L in [1,5]   → between x1 and x5
#     L in [5,10]  → between x5 and x10

MENTAL_KEYS = ["P", "A", "Er", "Rr"]

# ── mental STATE DB ──────────────────────────────────────────────────────────
# Each state has:
#   half_life  : cycles to drop to 50%
#   max_level  : accumulation ceiling
#   triggers   : concepts that activate it (1 unit per cycle if present)
#   levels     : vectors {P,A,Er,Rr} at x1, x5, x10
#                positives = sum, negatives = subtraction
#
# Negative states (raise A/Er) — fear, loneliness, anguish
# Positive states (raise P/Rr) — security, joy, belonging

MENTAL_STATES = {

    "fear": {
        # fast trigger, fast decay — like adrenaline
        # Always released — primary response to threat
        "half_life":  3,
        "max_level":  10.0,
        "triggers":   ["ghost", "danger", "threat", "dark", "scared", "attack", "shadow"],
        "tension_triggers": None,   # always active if concept present
        "levels": {
            1:  {"P":  0, "A": +8,  "Er": +10, "Rr":  0},
            5:  {"P":  0, "A": +22, "Er": +28, "Rr":  0},
            10: {"P":  0, "A": +40, "Er": +55, "Rr":  0},
        },
    },

    "loneliness": {
        # Always released — primary response to isolation
        "half_life":  8,
        "max_level":  10.0,
        "triggers":   ["alone", "dark", "room", "empty", "silence", "lost"],
        "tension_triggers": None,
        "levels": {
            1:  {"P":  0, "A": +6,  "Er":  0, "Rr": +4},
            5:  {"P":  0, "A": +18, "Er":  0, "Rr": +12},
            10: {"P":  0, "A": +32, "Er":  0, "Rr": +22},
        },
    },

    "anguish": {
        # Accumulates when fear + loneliness are present together
        "half_life":  5,
        "max_level":  10.0,
        "triggers":   ["ghost", "alone", "dark", "scared", "lost", "trapped"],
        "tension_triggers": None,
        "levels": {
            1:  {"P":  0, "A": +5,  "Er": +8,  "Rr": +3},
            5:  {"P":  0, "A": +15, "Er": +20, "Rr": +8},
            10: {"P":  0, "A": +28, "Er": +38, "Rr": +15},
        },
    },

    "security": {
        # Only released if there is active mental tension (fear/loneliness/anguish)
        # And the concept is NOT accompanied by threat
        # Analog of oxytocin — only useful in a stress context without active threat
        "half_life":  8,
        "max_level":  10.0,
        "triggers":    ["person", "safe", "light", "company", "calm", "familiar", "home"],
        "excludes":    ["threat", "danger", "aggressive", "attack", "shadow"],  # bloquean security
        "tension_triggers": {
            "states": ["fear", "loneliness", "anguish"],
            "threshold": 0.5,
        },
        "levels": {
            1:  {"P": +8,  "A":  0, "Er":  0, "Rr": +6},
            5:  {"P": +22, "A":  0, "Er":  0, "Rr": +18},
            10: {"P": +40, "A":  0, "Er":  0, "Rr": +32},
        },
    },

    "joy": {
        # Only released if there is active tension (sadness, anguish)
        # Analog of dopamine — reward in a context of need
        "half_life":  4,
        "max_level":  10.0,
        "triggers":   ["reward", "win", "play", "laugh", "food", "goal", "friend"],
        "tension_triggers": {
            "states": ["loneliness", "anguish"],
            "threshold": 0.3,
        },
        "levels": {
            1:  {"P": +6,  "A":  0, "Er": +10, "Rr":  0},
            5:  {"P": +18, "A":  0, "Er": +26, "Rr":  0},
            10: {"P": +35, "A":  0, "Er": +48, "Rr":  0},
        },
    },

    "calm": {
        # Only released if there is active tension
        # Analog of serotonin — stabilizes in a stress context
        "half_life":  12,
        "max_level":  10.0,
        "triggers":   ["calm", "breathe", "quiet", "safe", "place", "light"],
        "tension_triggers": {
            "states": ["fear", "loneliness", "anguish"],
            "threshold": 0.3,
        },
        "levels": {
            1:  {"P": +5,  "A": -2, "Er":  0, "Rr": +8},
            5:  {"P": +14, "A": -6, "Er":  0, "Rr": +20},
            10: {"P": +25, "A": -10,"Er":  0, "Rr": +35},
        },
    },

}

# Precomputar decay factors
for _state in MENTAL_STATES.values():
    _state["decay_factor"] = 0.5 ** (1.0 / _state["half_life"])

_ZERO_THRESHOLD = 0.05


# ── interpolation ─────────────────────────────────────────────────────────────

def _interpolate_push(levels_table, level):
    zero = {k: 0.0 for k in MENTAL_KEYS}
    l1   = levels_table[1]
    l5   = levels_table[5]
    l10  = levels_table[10]

    if level <= 0:
        return zero
    elif level <= 1:
        t = level / 1.0
        return {k: zero[k] + t * (l1[k] - zero[k]) for k in MENTAL_KEYS}
    elif level <= 5:
        t = (level - 1) / 4.0
        return {k: l1[k] + t * (l5[k] - l1[k]) for k in MENTAL_KEYS}
    else:
        t = min((level - 5) / 5.0, 1.0)
        return {k: l5[k] + t * (l10[k] - l5[k]) for k in MENTAL_KEYS}


# ── mental STATE SYSTEM ───────────────────────────────────────────────────────

# ── FORMULA PATH — mental twin of chemical_system.py's
# release_from_axis_push. Reuses the SAME 16-cell matrix
# (MATRIX_MODES) instead of duplicating it -- the metadata (name, half_life,
# peak_push, decay_factor) does not depend on which engine measures it, only the AXIS
# changes letter. self.matrix_levels is independent of self.levels
# (the old trigger-word system, untouched for now) -- body
# and mind can be in different phases of the same mode (see original
# CCM doc 4.8.1, 4-phase rebound somatic→mental→somatic→mental).
from systems.chemical_system import (
    MATRIX_MODES, MODES_BY_NAME, CATEGORIES, DEFAULT_GAINS,
)
import math

MENTAL_AXIS_MAP = {"P": "V", "A": "I", "Er": "Lv", "Rr": "Gv"}   # mental -> somatic cell (shared metadata)
MENTAL_AXES     = list(MENTAL_AXIS_MAP.keys())
_ZERO_THRESHOLD = 0.01


class MentalStateSystem:
    def __init__(self):
        self.levels = {name: 0.0 for name in MENTAL_STATES}
        # new: levels of the formula-driven matrix, in
        # parallel to self.levels above (trigger-word, untouched).
        self.matrix_levels = {name: 0.0 for name in MODES_BY_NAME}
        self.mental_gains  = {cat: dict(g) for cat, g in DEFAULT_GAINS.items()}
        self._matrix_cycle = 0

    # ── RELEASE ───────────────────────────────────────────────────────────────

    def release(self, state_name, amount=1.0):
        state = MENTAL_STATES.get(state_name)
        if not state:
            return
        self.levels[state_name] = min(
            state["max_level"],
            self.levels[state_name] + amount
        )

    def process_triggers(self, active_concepts):
        """
        Releases mental states based on active concepts in cycle.
        
        Primary states (fear, loneliness, anguish): always released
        if trigger concept present — like adrenaline/cortisol.
        
        Secondary states (security, calm, joy): only released
        if active mental tension (negative states above threshold)
        — like oxytocin/serotonin, only useful in a stress context.
        
        1 unit per matching concept.
        """
        concept_set = set(active_concepts) if active_concepts else set()

        for state_name, state in MENTAL_STATES.items():
            trigger_set = set(state["triggers"])
            hits = concept_set & trigger_set
            if not hits:
                continue

            # check excludes — concepts that block this state
            excludes = state.get("excludes", [])
            if excludes and (concept_set & set(excludes)):
                continue   # blocking concept present → not released

            # check tension_triggers if applicable
            tt = state.get("tension_triggers")
            if tt is not None:
                required_states = tt["states"]
                threshold       = tt["threshold"]
                tension_active  = any(
                    self.levels[s] >= threshold
                    for s in required_states
                    if s in self.levels
                )
                if not tension_active:
                    continue   # no active tension → not released

            self.release(state_name, float(len(hits)))

    # ── DECAY ─────────────────────────────────────────────────────────────────

    def decay(self):
        for name, state in MENTAL_STATES.items():
            self.levels[name] *= state["decay_factor"]
            if self.levels[name] < _ZERO_THRESHOLD:
                self.levels[name] = 0.0

    # ── PUSH ──────────────────────────────────────────────────────────────────

    def get_mental_push(self):
        """
        Returns combined mental vector of all active states.
        """
        result = {k: 0.0 for k in MENTAL_KEYS}
        for name, state in MENTAL_STATES.items():
            level = self.levels[name]
            if level < _ZERO_THRESHOLD:
                continue
            push = _interpolate_push(state["levels"], level)
            for k in MENTAL_KEYS:
                result[k] += push[k]
        return result

    # ── FORMULA PATH — mental twin of
    # chemical_system.py:resolve_winning_axis/release_from_axis_push/
    # get_somatic_push. See the comment next to MENTAL_AXIS_MAP above.

    def resolve_winning_mental_axis(self, category: str, raw_axis: dict, gains: dict = None):
        gains = gains if gains is not None else self.mental_gains
        row_gains = gains.get(category, DEFAULT_GAINS[category])

        finals = {}
        for axis in MENTAL_AXES:
            raw  = raw_axis.get(axis, 0.0)
            gain = row_gains.get(MENTAL_AXIS_MAP[axis], 5.0)   # gains saved with somatic label
            finals[axis] = raw * (0.5 + gain / 10.0)

        winning_axis = max(finals, key=finals.get)
        return winning_axis, finals

    def release_from_axis_push(self, category: str, axis_push: dict, gains: dict = None, scale: float = 1.0):
        """
        Same criterion as chemical_system.py:release_from_axis_push(),
        applied to the raw mental push (vec_m) instead of the somatic one.
        category must come from primary_evaluator_category_from_axis_push(
        vec_m, keys=MENTAL_KEYS, category_bias=self.mental_category_bias).
        """
        if category not in CATEGORIES:
            category = "neutral"

        magnitude = math.sqrt(sum(v * v for v in axis_push.values()))
        if magnitude < 1e-6:
            return None

        winning_axis, finals = self.resolve_winning_mental_axis(category, axis_push, gains)
        cell = (category, MENTAL_AXIS_MAP[winning_axis])
        mode = MATRIX_MODES[cell]

        amount = (finals[winning_axis] / 20.0) * scale
        if amount <= 0:
            return None

        self.matrix_levels[mode["name"]] = min(
            mode["max_level"], self.matrix_levels[mode["name"]] + amount
        )
        return winning_axis, finals[winning_axis]

    def decay_matrix(self):
        self._matrix_cycle += 1
        for mode_name, mode in MODES_BY_NAME.items():
            level = self.matrix_levels[mode_name] * mode["decay_factor"]
            self.matrix_levels[mode_name] = 0.0 if level < _ZERO_THRESHOLD else level

    def get_matrix_push(self):
        """Analogous to chemical_system.py::get_somatic_push() -- each mode
        pushes only its own mental axis (P/A/Er/Rr)."""
        result = {k: 0.0 for k in MENTAL_AXES}
        for cell, mode in MATRIX_MODES.items():
            level = self.matrix_levels[mode["name"]]
            if level < _ZERO_THRESHOLD:
                continue
            somatic_axis = cell[1]
            mental_axis = next(k for k, v in MENTAL_AXIS_MAP.items() if v == somatic_axis)
            result[mental_axis] += (level / 10.0) * mode["peak_push"]
        return result

    # ── STATUS ────────────────────────────────────────────────────────────────

    def status(self):
        out = {}
        for name, level in self.levels.items():
            if level >= _ZERO_THRESHOLD:
                state = MENTAL_STATES[name]
                push  = _interpolate_push(state["levels"], level)
                out[name] = {
                    "level":     round(level, 3),
                    "max_level": state["max_level"],
                    "half_life": state["half_life"],
                    "push":      {k: round(v, 2) for k, v in push.items()},
                }
        return out

    def summary_line(self):
        parts = [f"{n}={v:.2f}" for n, v in self.levels.items() if v >= _ZERO_THRESHOLD]
        return " | ".join(parts) if parts else "all clear"
