# systems/chemical_system.py — CCM v6 (single-formula redesign)
#
# REDESIGN —, see chemical_system_docs/chemical_system_redesign_conclusions.md
# ──────────────────────────────────────────────────────────────────────────
# The old design (7 chemicals with a name and a hand-calibrated {V,I,Lv,Gv}
# vector each) is gone. It is replaced by ONE scalable mechanism applied to
# the 16 cells of the response matrix (core/response_matrix.py):
#
#   stimulus → category (row: danger/benefit/neutral/unclassifiable)
#            → winning axis within that row (column: V/I/Gv/Lv), resolved
#              by  final_value = raw_reading(axis) × (0.5 + gain/10)
#            → the (category, axis) cell IS the "evaluative mode" that used to be
#              resolved by a named chemical — see MATRIX_MODES below.
#
# "Gain" is a per-character, per-cell trait (16 values, 1-10, future
# questionnaire — chemical_system_docs/chemical_system_axis_gain_full_matrix.md)
# that can override which axis wins a raw-input tie, exactly like the
# trauma/nuclear-memory override already documented for the somatic→mental
# temporal correction (the system-state notes). Until that questionnaire
# exists, DEFAULT_GAINS (all 5/10 → multiplier 1.0) makes this behave like
# plain "raw axis wins", so nothing breaks for characters without gains set.
#
# Each of the 16 modes keeps a biological reference name in comments (its
# dominant physiological system per chemical_system_physiological_effects.md)
# purely to justify its half-life/pattern — NOT as a separate channel to
# program. There is only ONE release/decay/push mechanism, applied 16 times
# with different parameters.
#
# WHAT'S IMPLEMENTED HERE (closed per the design docs):
#   - MATRIX_MODES: the 16 modes, one per (category, axis) cell.
#   - release_from_axis_push(category, axis_push, gains): the gain-weighted
#     tie-break formula ( of the conclusions doc), applied to whichever
#     row is active this cycle — not just Danger.
#   - Opponent-process rebound ( mechanism 2): Attack, Accept, Cooperate,
#     Investigate and Suppress are flagged as rebound-prone; when their level
#     retreats hard from a peak, a delayed counter-push is scheduled and later
#     lands on the Danger row (modeled as the generic "distress" row — see
#     _fire_rebound docstring for why, and for what's still a judgment call).
#   - Backward-compat shims (LEGACY_TRIGGER_TO_MODES / legacy_level /
#     process_triggers) so existing hand-authored triggers (db/db_concepts.py,
#     motors/internal_somatic.py) that still say "adrenaline"/"cortisol"/etc.
#     keep working, routed into the new modes instead of a discrete channel.
#
# WHAT'S STILL PENDING (explicitly open in the design docs, not guessed here):
#   - Real per-species/per-individual min/max/equilibrium ranges — today's
#     half_life/max_level/peak_push numbers are a first-pass, qualitative
#     read of "peak/plateau/tonic" from chemical_system_physiological_effects.md,
#     not the calibrated CCM_*.xlsx data (which itself has 3 open audit bugs,
#     see chemical_system_docs/chemical_system_redesign_conclusions.md).
#   - Rate-of-change (delta/time) as a second trigger dimension for sensory
#     thresholds  — not modeled here, this file only sees the already-
#     resolved axis_push per cycle, not its velocity.
#   - Final question count / wording for the 16 gain questions (character
#     questionnaire) — the `gains` dict shape is ready to receive them
#     (character/injector.py has a hook), the questionnaire itself doesn't.

import math
from layers.emotion_mapper import get_saturation_label

SOMATIC_KEYS = ["V", "I", "Lv", "Gv"]
CATEGORIES   = ["danger", "benefit", "neutral", "unclassifiable"]
AXES         = ["V", "I", "Gv", "Lv"]

# ── THE 16 MODES ─────────────────────────────────────────────────────────────
# One entry per (category, axis) cell of core/response_matrix.RESPONSE_MATRIX.
# "name" matches the verb already used there, so a mode and its matrix cell
# are the same concept, addressed two ways (the matrix cares about the verb
# for phrasing; this file cares about it for the physiological channel).
#
# pattern   : shape of the curve, from chemical_system_physiological_effects.md
#             ("peak", "peak_slow", "peak_moderate", "plateau", "plateau_brief",
#              "tonic", "collapse", "brake", "brake_active", "brake_passive")
# half_life : cycles to drop to 50% — peaks decay fast, plateaus/tonic slow
# peak_push : somatic push magnitude on this mode's own axis at level=10
#             (single-axis push only — the new design doesn't mix axes the
#             way the old 4-D chemical vectors did; the column IS the axis)
# rebound   : None, or {"delay", "fraction", "target_axis"} — see
#             _maybe_schedule_rebound() / _fire_rebound()
# ref       : biological reference system, comment-only (chosen per
#             chemical_system_physiological_effects.md)

MATRIX_MODES = {

    # ── DANGER ────────────────────────────────────────────────────────────
    ("danger", "V"): {
        "name": "attack", "emotion": "anger", "emotion_ladder": {"neutral": "irritated", "mild": "annoyed", "active": "angry", "intense": "furious", "saturated": "enraged", "collapse": "blind rage"}, "pattern": "peak", "half_life": 2, "max_level": 10.0,
        "peak_push": 50.0, "ref": "acute catecholamines (adrenaline+noradrenaline)",
        "rebound": {"delay": 3, "fraction": 0.15, "target_axis": "I"},
    },
    ("danger", "I"): {
        "name": "surrender", "emotion": "despair", "emotion_ladder": {"neutral": "discouraged", "mild": "downhearted", "active": "despairing", "intense": "hopeless", "saturated": "devastated", "collapse": "shattered"}, "pattern": "collapse", "half_life": 6, "max_level": 10.0,
        "peak_push": 30.0, "ref": "dorsal vagal + endogenous opioids (defensive collapse)",
        "rebound": None,  # protective during, creates no debt on exit — §3.5 mechanism 1
    },
    ("danger", "Gv"): {
        "name": "protect", "emotion": "worry", "emotion_ladder": {"neutral": "concerned", "mild": "worried", "active": "troubled", "intense": "distressed", "saturated": "overwhelmed", "collapse": "frantic"},
        # positive_ladder ( worried/valiant review): the SAME
        # protect cell, but for when the character is still viable/
        # present (resourced) instead of inviable/absent (depleted) --
        # see get_emotion_label's quadrant_positive param and the
        # comment in cycle_manager_v5.py:_build_output for how that
        # sign gets here. Deliberately reuses the SAME family already
        # in layers/emotion_mapper.py's present-rational branch
        # (confident/resolute/secure) at the low/mid tiers instead of
        # inventing new words there,: the positive
        # register already existed, protect just never reached for it.
        # "valiant"/"heroic"/"unbreakable" are new at the top two
        # tiers -- present-rational's own ladder tops out at "resolute",
        # which reads as composed/steady, not the active bravery a
        # protector defending someone else under real danger should hit
        # at high magnitude (this cell IS "danger" category, unlike
        # emotion_mapper's present-rational which isn't tied to a
        # specific category at all).
        "positive_ladder": {"neutral": "steady", "mild": "confident", "active": "resolute", "intense": "valiant", "saturated": "heroic", "collapse": "unbreakable"},
        # half_life 10->72: cortisol's real plasma half-life
        # (~90 min) is ~36x epinephrine/noradrenaline's (~2.5 min) --
        # attack/flee below anchor half_life=2, so 2*36=72 keeps protect's
        # ratio to them grounded in that real ratio instead of the
        # original qualitative guess (10, only 5x attack/flee -- this
        # file's own header already flagged half_life as "a first-pass
        # qualitative read... not the calibrated data", this is that
        # calibration for this one cell). Sources: epinephrine plasma
        # t1/2 ~2-3min (NIH StatPearls), cortisol plasma t1/2 ~90min
        # (adrenal axis references) -- both well-established, unlike the
        # other cells here which don't have as clean a real-world anchor.
        "pattern": "plateau", "half_life": 72, "max_level": 10.0,
        "peak_push": 25.0, "ref": "cortisol (HPA axis), sustained plateau",
        "rebound": None,
    },
    ("danger", "Lv"): {
        "name": "flee", "emotion": "fear", "emotion_ladder": {"neutral": "wary", "mild": "uneasy", "active": "anxious", "intense": "fear", "saturated": "panic", "collapse": "terror"}, "pattern": "peak", "half_life": 2, "max_level": 10.0,
        "peak_push": 48.0, "ref": "acute catecholamines, same family as attack",
        "rebound": None,
    },

    # ── BENEFIT ───────────────────────────────────────────────────────────
    ("benefit", "V"): {
        "name": "accept", "emotion": "joy", "emotion_ladder": {"neutral": "pleased", "mild": "glad", "active": "happy", "intense": "joyful", "saturated": "elated", "collapse": "euphoric"}, "pattern": "peak", "half_life": 2, "max_level": 10.0,
        "peak_push": 45.0, "ref": "dopamine (reward pathway)",
        "rebound": {"delay": 3, "fraction": 0.35, "target_axis": "I"},
    },
    ("benefit", "I"): {
        "name": "deny", "emotion": "restraint", "emotion_ladder": {"neutral": "composed", "mild": "restrained", "active": "controlled", "intense": "disciplined", "saturated": "rigid", "collapse": "repressed"}, "pattern": "brake", "half_life": 5, "max_level": 10.0,
        "peak_push": 18.0, "ref": "serotonin (prefrontal inhibition / self-control)",
        "rebound": None,
    },
    ("benefit", "Gv"): {
        "name": "cooperate", "emotion": "trust", "emotion_ladder": {"neutral": "friendly", "mild": "warm", "active": "trusting", "intense": "affectionate", "saturated": "devoted", "collapse": "adoring"}, "pattern": "peak_slow", "half_life": 5, "max_level": 10.0,
        "peak_push": 42.0, "ref": "oxytocin",
        "rebound": {"delay": 4, "fraction": 0.25, "target_axis": "I"},
    },
    ("benefit", "Lv"): {
        "name": "ignore_benefit", "emotion": "contentment", "emotion_ladder": {"neutral": "fine", "mild": "content", "active": "satisfied", "intense": "fulfilled", "saturated": "serene", "collapse": "blissful"}, "pattern": "tonic", "half_life": 14, "max_level": 10.0,
        "peak_push": 6.0, "ref": "baseline serotonin / no strong signal",
        "rebound": None,
    },

    # ── NEUTRAL / CLASSIFIABLE ────────────────────────────────────────────
    ("neutral", "V"): {
        "name": "observe", "emotion": "interest", "emotion_ladder": {"neutral": "attentive", "mild": "interested", "active": "curious", "intense": "engrossed", "saturated": "fascinated", "collapse": "captivated"}, "pattern": "tonic", "half_life": 14, "max_level": 10.0,
        "peak_push": 8.0, "ref": "low tonic dopamine (exploratory)",
        "rebound": None,
    },
    ("neutral", "I"): {
        "name": "ignore_neutral", "emotion": "calm", "emotion_ladder": {"neutral": "at ease", "mild": "calm", "active": "relaxed", "intense": "tranquil", "saturated": "still", "collapse": "placid"}, "pattern": "tonic", "half_life": 14, "max_level": 10.0,
        "peak_push": 6.0, "ref": "baseline serotonin / no strong signal",
        "rebound": None,
    },
    ("neutral", "Gv"): {
        "name": "group", "emotion": "belonging", "emotion_ladder": {"neutral": "included", "mild": "comfortable", "active": "connected", "intense": "close", "saturated": "bonded", "collapse": "unified"}, "pattern": "tonic", "half_life": 14, "max_level": 10.0,
        "peak_push": 8.0, "ref": "low oxytocin / ventral vagal tone at rest",
        "rebound": None,
    },
    ("neutral", "Lv"): {
        "name": "formulate", "emotion": "alertness", "emotion_ladder": {"neutral": "aware", "mild": "alert", "active": "focused", "intense": "sharp", "saturated": "hyperalert", "collapse": "on edge"}, "pattern": "tonic", "half_life": 14, "max_level": 10.0,
        "peak_push": 9.0, "ref": "low tonic noradrenaline",
        "rebound": None,
    },

    # ── UNCLASSIFIABLE ────────────────────────────────────────────────────
    ("unclassifiable", "V"): {
        "name": "investigate", "emotion": "wonder", "emotion_ladder": {"neutral": "curious", "mild": "intrigued", "active": "wondering", "intense": "amazed", "saturated": "awestruck", "collapse": "astonished"}, "pattern": "peak_moderate", "half_life": 3, "max_level": 10.0,
        "peak_push": 32.0, "ref": "dopamine (novelty/curiosity circuit)",
        "rebound": {"delay": 3, "fraction": 0.15, "target_axis": "I"},
    },
    ("unclassifiable", "I"): {
        "name": "desist", "emotion": "boredom", "emotion_ladder": {"neutral": "indifferent", "mild": "bored", "active": "restless", "intense": "listless", "saturated": "apathetic", "collapse": "numb"}, "pattern": "brake_passive", "half_life": 6, "max_level": 10.0,
        "peak_push": 14.0, "ref": "dopamine drop / motivational withdrawal",
        "rebound": None,
    },
    ("unclassifiable", "Gv"): {
        "name": "signal", "emotion": "concern", "emotion_ladder": {"neutral": "watchful", "mild": "concerned", "active": "alarmed", "intense": "urgent", "saturated": "desperate", "collapse": "distraught"}, "pattern": "plateau_brief", "half_life": 4, "max_level": 10.0,
        "peak_push": 18.0, "ref": "vasopressin / targeted oxytocin",
        "rebound": None,
    },
    ("unclassifiable", "Lv"): {
        "name": "suppress", "emotion": "tension", "emotion_ladder": {"neutral": "guarded", "mild": "tense", "active": "strained", "intense": "clenched", "saturated": "taut", "collapse": "frozen"}, "pattern": "brake_active", "half_life": 8, "max_level": 10.0,
        "peak_push": 20.0, "ref": "GABA (active inhibition)",
        "rebound": {"delay": 2, "fraction": 0.40, "target_axis": "I"},
    },
}

# Precompute decay factors + reverse lookup by mode name
for _mode in MATRIX_MODES.values():
    _mode["decay_factor"] = 0.5 ** (1.0 / _mode["half_life"])

MODES_BY_NAME = {mode["name"]: mode for mode in MATRIX_MODES.values()}
CELL_BY_NAME  = {mode["name"]: cell for cell, mode in MATRIX_MODES.items()}


def get_emotion_label(category: str, axis: str, distance: float, quadrant_positive: bool = None) -> str:
    """
    FUSION (2026-09-05) of the two emotion systems that used to run in
    parallel: MATRIX_MODES already picks WHICH emotion family a
    (category, axis) cell belongs to (fear/anger/joy/trust/...), and
    layers/emotion_mapper.py already knows how to grade a raw distance
    into 6 intensity levels (neutral/mild/active/intense/saturated/
    collapse — get_saturation_label()). Neither needed to be rebuilt:
    this just looks up the SAME cell's "emotion_ladder" at that level,
    e.g. get_emotion_label("danger", "Lv", 90) -> "panic" (danger/Lv is
    the fear family; distance 90 grades to "saturated" on that ladder).

    quadrant_positive (2026-09-10, worried/valiant review): the ORIGINAL
    fusion above deliberately dropped quadrant from the word choice --
    fine for most cells, but wrong for `protect`, where the SAME mode
    reads as "worried/frantic" while depleted (inviable/absent) and as
    "confident/valiant" while still resourced (viable/present) -- two
    real, different emotions, not two intensities of one. When True and
    the cell has a "positive_ladder", that ladder is used instead of
    the regular one. Cells without a "positive_ladder" ignore this
    param entirely and behave exactly as before -- opt-in per cell, not
    a system-wide behavior change.

    Falls back to the cell's base "emotion" name if the cell or its
    ladder isn't found (shouldn't happen for any of the 16 real cells).
    """
    cell = MATRIX_MODES.get((category, axis))
    if not cell:
        return "neutral"
    level = get_saturation_label(distance)
    ladder = cell.get("emotion_ladder", {})
    if quadrant_positive and "positive_ladder" in cell:
        ladder = cell["positive_ladder"]
    return ladder.get(level, cell.get("emotion", "neutral"))

# ── DEFAULT GAINS ────────────────────────────────────────────────────────────
# 5/10 on every cell → multiplier (0.5 + 5/10) = 1.0 → raw axis magnitude
# decides the winner, unchanged. Real per-character gains come later from the
# 16-question questionnaire (chemical_system_docs/chemical_system_axis_gain_*.md);
# character/injector.py already has a hook (`chemical_gains` in character.json)
# to set these once that questionnaire exists.
DEFAULT_GAINS = {cat: {axis: 5.0 for axis in AXES} for cat in CATEGORIES}

# ── LEGACY COMPATIBILITY ─────────────────────────────────────────────────────
# Old hand-authored triggers (db/db_concepts.py "related" tags, and
# motors/internal_somatic.py's reflex releases) still say "adrenaline",
# "cortisol", etc. Route those names into the mode(s) that now cover that
# same physiological reference, per chemical_system_physiological_effects.md,
# so nothing upstream needs to be rewritten.
LEGACY_TRIGGER_TO_MODES = {
    "adrenaline":     ["attack", "flee"],
    "noradrenaline":  ["attack", "flee"],
    "cortisol":       ["protect"],
    "dopamine":       ["accept", "investigate"],
    "serotonin":      ["deny"],
    "oxytocin":       ["cooperate", "signal"],
    "endorphins":     ["surrender"],
    "testosterone":   ["attack"],
}

# Legacy concept-name trigger lists, reassigned from the old CHEMICALS table
# to the new modes that inherited each chemical's physiological role.
LEGACY_MODE_TRIGGERS = {
    "attack":      ["danger", "ghost", "threat", "scared", "attack", "shock"],
    "flee":        ["danger", "ghost", "threat", "scared", "attack", "shock"],
    "protect":     ["danger", "threat", "ghost", "dark", "alone", "scared"],
    "surrender":   ["run", "breathe", "walk", "food", "water"],
    "accept":      ["food", "safe", "calm", "reward", "win", "goal", "home"],
    "investigate": ["food", "safe", "calm", "reward", "win", "goal", "home"],
    "deny":        ["calm", "safe", "light", "breathe", "quiet", "place"],
    "cooperate":   ["person", "safe", "calm", "breathe"],
    "signal":      ["person", "safe", "calm", "breathe"],
}
LEGACY_MODE_VITAL_TRIGGERS = {
    "attack":    [("temperature", 2.0)],
    "flee":      [("temperature", 2.0)],
    "protect":   [("energy", 2.0), ("hunger", 2.0)],
    "surrender": [("energy", 2.0)],
}

def legacy_level(levels: dict, legacy_name: str) -> float:
    """
    Module-level helper — reads a level the OLD way, by chemical name (e.g.
    "adrenaline"), from a raw `levels` dict (ChemicalSystem.levels). Exists
    standalone (not just as a ChemicalSystem method) because some callers
    — motors/internal_somatic.py's reflex functions — only receive the
    plain levels dict, not the ChemicalSystem instance. Sums the modes
    that inherited that legacy chemical's physiological role.
    """
    mapped = LEGACY_TRIGGER_TO_MODES.get(legacy_name)
    if not mapped:
        return 0.0
    return sum(levels.get(m, 0.0) for m in mapped)


# ── DEPLETION (paper, "Saturation and Regulation Failure") ────────────
# Added The paper says that when the somatic engine saturates "the chemical system can no
# longer release effective modulators" (HPA-axis depletion, Selye 1956). Before this, nothing limited
# release: every input -- calm ones too -- added final/20 to a mode (breeze ~6.7, birds ~8.75 of a max
# of 10), the modes sat near their maximum, their push held the somatic engine up, and the engine
# never came back down (see MEMORY_VS_PAPER.md, finding E).
#
# Two parts, both in release_from_axis_push:
#   1. RESERVE: every release spends a shared reserve (1.0 = full) and the reserve refills slowly in
#      decay. A burst of releases therefore leaves the system with LESS release capacity than its
#      normal (a refractory period), so levels sag and the engine can settle.
#   2. SATURATION BLOCK: while the somatic engine is "saturated" or "collapse" (get_saturation_label)
#      nothing is released at all; external input is needed to recover.
# Set DEPLETION_ENABLED = False to get the exact previous behaviour.
DEPLETION_ENABLED      = True
DEPLETION_INTERNAL     = False        # also apply the reserve to release() (internal somatic motor, graph
                                      # multipliers). Tried and left OFF: with NO input a resting
                                      # character drifts to D~100 (heart rate -> 180 bpm), but spending the
                                      # reserve on the internal motor's small releases did not stop it (the
                                      # loop is driven by the +3 bpm/cycle of "viable-localized" and the x7
                                      # adrenaline weight, see MEMORY_VS_PAPER.md finding F).
RESERVE_CAPACITY       = 10.0 / 3.0   # release "units" that empty a full reserve (experimental value)
RESERVE_REGEN_PER_CYCLE = 0.06        # reserve refilled per cycle (experimental value)
_SATURATED_LABELS      = ("saturated", "collapse")

_ZERO_THRESHOLD        = 0.05
_REBOUND_TRIGGER_LEVEL = 5.0   # a mode must have reached at least this high...
_REBOUND_RETREAT_RATIO = 0.4   # ...and dropped below this fraction of its peak...
                                # ...before a rebound is scheduled (once per peak).


# ── CHEMICAL SYSTEM ───────────────────────────────────────────────────────────

class ChemicalSystem:
    def __init__(self, gains: dict = None):
        self.levels  = {name: 0.0 for name in MODES_BY_NAME}
        self.gains   = gains if gains is not None else DEFAULT_GAINS
        self._cycle            = 0
        self._peak_tracker     = {name: 0.0 for name in MODES_BY_NAME}
        self._rebound_armed    = set()   # modes with a rebound already scheduled for this peak
        self._pending_rebounds = []      # [{"fire_at_cycle","target_axis","amount","source_mode"}]
        self._reserve          = 1.0     # release reserve, see DEPLETION above (1.0 = full)

    # ── RELEASE (generic — accepts a mode name OR a legacy chemical name) ────

    def _spend_reserve(self, amount):
        """Scales `amount` by the current reserve and spends it (see DEPLETION above)."""
        amount *= self._reserve
        self._reserve = max(0.0, self._reserve - amount / RESERVE_CAPACITY)
        return amount

    def release(self, name, amount=1.0):
        """
        Releases into a mode directly (`name` is a MATRIX_MODES mode name,
        e.g. "attack"), or via legacy alias (`name` is an old chemical name,
        e.g. "adrenaline" — split across the modes that inherited its role).
        Unknown names are ignored, same as the old `if not chem: return`.
        """
        if DEPLETION_ENABLED and DEPLETION_INTERNAL:
            amount = self._spend_reserve(amount)
        if name in self.levels:
            self._release_mode(name, amount)
            return

        mapped = LEGACY_TRIGGER_TO_MODES.get(name)
        if mapped:
            for mode_name in mapped:
                self._release_mode(mode_name, amount / len(mapped))

    def _release_mode(self, mode_name, amount):
        mode = MODES_BY_NAME[mode_name]
        self.levels[mode_name] = min(mode["max_level"], self.levels[mode_name] + amount)
        self._peak_tracker[mode_name] = max(self._peak_tracker[mode_name], self.levels[mode_name])

    def legacy_level(self, legacy_name: str) -> float:
        """Instance-method convenience wrapper — see module-level legacy_level()."""
        return legacy_level(self.levels, legacy_name)

    def process_triggers(self, active_concepts, vitality_stats=None):
        """
        LEGACY PATH — kept for backward compatibility with hand-authored
        concepts (e.g. "ghost" in db/db_concepts.py) that rely on a fixed
        concept-name -> trigger list, now reassigned to modes (see
        LEGACY_MODE_TRIGGERS above) instead of named chemicals. For the
        ~5,000 words in db/db_lexicon.py with no hand-written triggers,
        this does nothing — use release_from_axis_push() instead, which
        works for ANY concept via the gain-weighted formula, no per-word
        list needed.
        """
        concept_set = set(active_concepts) if active_concepts else set()

        for mode_name, triggers in LEGACY_MODE_TRIGGERS.items():
            if concept_set & set(triggers):
                self.release(mode_name, 1.0)

            if vitality_stats:
                for need_name, threshold in LEGACY_MODE_VITAL_TRIGGERS.get(mode_name, []):
                    need = vitality_stats.get(need_name)
                    if need is None:
                        continue
                    val = need.get("value", 10.0)
                    if val <= threshold:
                        depth = 1.0 - (val / threshold)
                        self.release(mode_name, depth * 0.5)

    # ── FORMULA PATH — the actual redesign ───────────────────────────────────

    def resolve_winning_axis(self, category: str, raw_axis: dict, gains: dict = None):
        """
        chemical_system_redesign_conclusions.md §6.3:
            final_value(axis) = raw_reading(axis) × (0.5 + gain(axis)/10)
            winning_axis = axis with the highest final_value among the 4 of the row

        `raw_axis` is this cycle's raw somatic push (vec_s-style dict, keys
        V/I/Lv/Gv). `gains` is a {category: {axis: 1-10}} dict (defaults to
        DEFAULT_GAINS / self.gains — see class docstring on why 5 is neutral).
        Returns (winning_axis, {axis: final_value, ...}).
        """
        gains = gains if gains is not None else self.gains
        row_gains = gains.get(category, DEFAULT_GAINS[category])

        finals = {}
        for axis in AXES:
            raw = raw_axis.get(axis, 0.0)
            gain = row_gains.get(axis, 5.0)
            finals[axis] = raw * (0.5 + gain / 10.0)

        winning_axis = max(finals, key=finals.get)
        return winning_axis, finals

    def release_from_axis_push(self, category: str, axis_push: dict, gains: dict = None, scale: float = 1.0,
                               somatic_dist: float = None):
        """
        FORMULA-BASED release — replaces the old cosine-similarity-against-
        named-chemical-vectors approach. Applied to whichever row (category)
        the Primary Evaluator assigned to this cycle's stimulus
        (core/response_matrix.primary_evaluator_category), using this
        cycle's raw axis push (axis_push, e.g. vec_s) plus the character's
        gain for that row (self.gains / DEFAULT_GAINS if none set yet).

        `category` must be one of CATEGORIES; unknown values fall back to
        "neutral" (the lowest-consequence row) rather than raising, since
        upstream category detection is itself still a placeholder heuristic
        (core/response_matrix.py primary_evaluator_category docstring).

        Returns (winning_axis, finals[winning_axis]) so the caller can look
        up this cycle's emotion label via get_emotion_label(category,
        winning_axis, finals[winning_axis]) — None if the push was too
        small to release anything.
        """
        if category not in CATEGORIES:
            category = "neutral"

        magnitude = math.sqrt(sum(v * v for v in axis_push.values()))
        if magnitude < 1e-6:
            return None

        winning_axis, finals = self.resolve_winning_axis(category, axis_push, gains)
        mode = MATRIX_MODES[(category, winning_axis)]

        amount = (finals[winning_axis] / 20.0) * scale
        if amount <= 0:
            return None
        if DEPLETION_ENABLED:
            if somatic_dist is not None and get_saturation_label(somatic_dist) in _SATURATED_LABELS:
                amount = 0.0                                   # saturated: cannot release
            else:
                amount = self._spend_reserve(amount)           # low reserve -> weaker release
        if amount > 0:
            self._release_mode(mode["name"], amount)
        # the caller still gets the winning axis/value (emotion label) even if nothing was released
        return winning_axis, finals[winning_axis]

    # ── DECAY + OPPONENT-PROCESS REBOUND ─────────────────────────────────────

    def decay(self):
        self._cycle += 1
        if DEPLETION_ENABLED:
            self._reserve = min(1.0, self._reserve + RESERVE_REGEN_PER_CYCLE)

        for mode_name, mode in MODES_BY_NAME.items():
            prev  = self.levels[mode_name]
            level = prev * mode["decay_factor"]
            if level < _ZERO_THRESHOLD:
                level = 0.0

            if mode["rebound"] is not None:
                self._maybe_schedule_rebound(mode_name, mode, prev, level)

            self.levels[mode_name] = level

        self._fire_due_rebounds()

    def _maybe_schedule_rebound(self, mode_name, mode, prev_level, new_level):
        """
        §3.5 mechanism 2 (opponent-process): a strong peak that retreats
        hard leaves a delayed counter-push. Fires once per peak (armed/
        disarmed via _rebound_armed) so a slow decay doesn't spam rebounds
        every single cycle while it crosses the retreat ratio.
        """
        peak = self._peak_tracker[mode_name]
        already_armed = mode_name in self._rebound_armed

        if (not already_armed
                and peak >= _REBOUND_TRIGGER_LEVEL
                and prev_level >= peak * _REBOUND_RETREAT_RATIO
                and new_level < peak * _REBOUND_RETREAT_RATIO):
            cfg = mode["rebound"]
            self._pending_rebounds.append({
                "fire_at_cycle": self._cycle + cfg["delay"],
                "target_axis":   cfg["target_axis"],
                "amount":        peak * cfg["fraction"],
                "source_mode":   mode_name,
            })
            self._rebound_armed.add(mode_name)

        if new_level < _ZERO_THRESHOLD:
            # fully cleared — reset so the next peak can arm its own rebound
            self._peak_tracker[mode_name] = 0.0
            self._rebound_armed.discard(mode_name)

    def _fire_due_rebounds(self):
        """
        Rebounds land on the Danger row (target_axis picks which of Attack/
        Surrender/Protect/Flee absorbs it) — modeling the "crash"/anxiety/
        hyperexcitation of opponent-process as generic distress. This
        specific landing spot is an implementation choice made to keep the
        mechanism concrete now; the design docs flag the exact wiring here
        as still open (chemical_system_redesign_conclusions.md §6.5#1).
        """
        still_pending = []
        for reb in self._pending_rebounds:
            if reb["fire_at_cycle"] <= self._cycle:
                mode = MATRIX_MODES.get(("danger", reb["target_axis"]))
                if mode:
                    self._release_mode(mode["name"], reb["amount"])
            else:
                still_pending.append(reb)
        self._pending_rebounds = still_pending

    # ── PUSH ──────────────────────────────────────────────────────────────────

    def get_somatic_push(self):
        """
        Each mode pushes ONLY along its own axis (the column IS the axis —
        no cross-axis mixing like the old 4-D chemical vectors). Magnitude
        scales linearly from 0 at level=0 to `peak_push` at level=10.
        """
        result = {k: 0.0 for k in SOMATIC_KEYS}
        for mode_name, mode in MODES_BY_NAME.items():
            level = self.levels[mode_name]
            if level < _ZERO_THRESHOLD:
                continue
            axis = CELL_BY_NAME[mode_name][1]
            result[axis] += (level / 10.0) * mode["peak_push"]
        return result

    # ── STATUS ────────────────────────────────────────────────────────────────

    def status(self):
        out = {}
        for mode_name, level in self.levels.items():
            if level >= _ZERO_THRESHOLD:
                mode = MODES_BY_NAME[mode_name]
                category, axis = CELL_BY_NAME[mode_name]
                out[mode_name] = {
                    "level":      round(level, 3),
                    "category":   category,
                    "axis":       axis,
                    "pattern":    mode["pattern"],
                    "max_level":  mode["max_level"],
                    "half_life":  mode["half_life"],
                }
        return out

    def summary_line(self):
        parts = [f"{n}={v:.2f}" for n, v in self.levels.items() if v >= _ZERO_THRESHOLD]
        return " | ".join(parts) if parts else "all clear"
