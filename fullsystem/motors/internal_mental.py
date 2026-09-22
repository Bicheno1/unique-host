# motors/internal_mental.py — CCM v8
#
# mental INTERNAL ENGINE — cognitive self-regulation (real, not passthrough)
#
# CHANGE the previous version was a passthrough of chem_m
# (MentalStateSystem.get_mental_push) -- but chem_m is ALREADY applied
# directly in PING 2 (cycle_manager_v5.py, apply_internal(chem_m)).
# Forwarding it here and applying it again was DOUBLE COUNTING the same
# push, every cycle. This module now only carries the NEW push:
# memory evocation (what the original comment promised
# -- "evocation, reflexes" -- and never did).
#
# THE IDEA:
#   The system ASKS first (verbally -- "I'm thirsty", "would you
#   keep me company?" -- output layer, not implemented yet).
#   If the need is NOT resolved externally, only then does the internal
#   engine compensate:
#     - somatic: chemicals that mimic the body sustaining itself without the
#       resource (autophagy, etc) -- with a clear ceiling. This already exists via
#       mind_stats/vitality_stats (pressure is proportional to the
#       deficit, capped by the maximum deficit -- nothing to touch
#       there, the ceiling is already in place).
#     - mental: looks for a REAL associated memory (never invented) and
#       pushes LIGHTLY, for a short time, decaying fast -- a brief
#       relief, not a sustained solution.
#
# WHY a cooldown + short half_life (and not re-firing every cycle the
# deficit stays high): that is EXACTLY the defect of Bug C
# (chemical_system.py process_triggers legacy) -- flat injection
# every cycle beats slow decay and the system never returns to
# rest. An evocation echo has to be the opposite: fire once,
# decay fast, and wait out a cooldown before it can fire
# again -- so the character can "console itself" with a memory,
# but doesn't get hooked on it.

from db.db_mental import MENTAL_KEYS

DEFICIT_THRESHOLD = 0.4    # the mind_stat must be at least 40% below its baseline
COOLDOWN_CYCLES    = 6      # cycles before the SAME stat can evoke again
ECHO_HALF_LIFE     = 2      # cycles to fall to 50% -- brief on purpose ("short-lived and decaying")
ECHO_SCALE         = 15.0   # magnitude of the light nudge -- placeholder, tune by testing

_ECHO_DECAY = 0.5 ** (1.0 / ECHO_HALF_LIFE)

# Which concepts evoke looks for in memory when each real mental need
# is in deficit. PLACEHOLDER -- tunable per
# character or as a general rule; today it is only a reasonable
# starting point. The 4 names are the real roots of
# systems/vital_system.py:MENTAL_NEEDS (company/purpose/security/
# structure) -- NOT motors/mind_stats.py, which is a disconnected
# duplicate (nothing ever updates it; see note below).
STAT_CONCEPT_MAP = {
    "company":   ["person", "friend", "dog", "family"],
    "purpose":   ["goal", "reward", "win"],
    "security":  ["safe", "home", "protect"],
    "structure": ["place", "home"],
}

# sanity is not a root with its own push (it is a derived "tree", see
# vital_system.py::SANITY_TREE) -- it has no comfort_threshold or
# critical_threshold defined, so its deficit is approximated here with
# its own, looser thresholds, instead of the roots' formula.
SANITY_COMFORT  = 6.0
SANITY_CRITICAL = 2.0
SANITY_CONCEPTS = ["calm", "familiar", "light"]


class MentalEvocation:
    """
    Brief, decreasing echoes triggered by deficits in REAL mental
    needs (systems/vital_system.py::MENTAL_NEEDS + sanity).
    This is NOT a persistent level like chemical/mental_state -- each echo
    dies out on its own within a handful of cycles and cannot be re-triggered
    until the cooldown has passed, even if the deficit is still there.

    NOTE about motors/mind_stats.py: that file defines the same 5
    names (company/purpose/security/structure/sanity) with almost the
    same mental_push values, but it is an abandoned duplicate --
    nothing ever calls its update(), so its values never move
    from its own baseline. The live version, connected to the real
    concepts of the scene (NEED_INPUTS: "friend"→company, "danger"→
    security, etc.), is the one in vital_system.py. That is why this class reads
    from `vitality` (VitalityStats), not from `mind_stats`.
    """

    def __init__(self):
        self._echo_level = {}              # stat_name -> current magnitude (0..1)
        self._echo_vec   = {}              # stat_name -> direction {P,A,Er,Rr} frozen at trigger time
        self._last_trigger_cycle = {}      # stat_name -> cycle of the last trigger
        self._cycle = 0
        self.last_unmet_needs = []         # stats in deficit with no real memory to evoke (for output, later)

    def _deficit(self, vitality, stat_name):
        vs = vitality._vs
        if stat_name == "sanity":
            val = vs.sanity["value"]
            if val >= SANITY_COMFORT:
                return 0.0
            if val <= SANITY_CRITICAL:
                return 1.0
            return (SANITY_COMFORT - val) / (SANITY_COMFORT - SANITY_CRITICAL)
        need = vs.mental.get(stat_name)
        if not need:
            return 0.0
        return vs._compute_pressure(stat_name, need)  # same formula the rest of the system uses

    def tick(self, vitality, memory, current_mental_distance):
        """
        vitality   : instance of motors.vitality_stats.VitalityStats
                     (self.vitality in cycle_manager_v5 -- NOT self.mind)
        memory     : instance of systems.memory_system.MemorySystem (memory_m)
        current_mental_distance : current mental distance (for evoke())
        Returns the {P,A,Er,Rr} push vector for this cycle.
        """
        self._cycle += 1
        self.last_unmet_needs = []

        # decay of the active echoes
        for name in list(self._echo_level):
            self._echo_level[name] *= _ECHO_DECAY
            if self._echo_level[name] < 0.05:
                del self._echo_level[name]
                del self._echo_vec[name]

        all_stats = list(STAT_CONCEPT_MAP.keys()) + ["sanity"]
        for stat_name in all_stats:
            deficit = self._deficit(vitality, stat_name)
            if deficit < DEFICIT_THRESHOLD:
                continue

            last = self._last_trigger_cycle.get(stat_name, -999)
            if self._cycle - last < COOLDOWN_CYCLES:
                continue  # still in cooldown -- let it decay before trying again

            concepts = STAT_CONCEPT_MAP.get(stat_name) or SANITY_CONCEPTS
            evoked = memory.evoke(concepts, current_mental_distance) if concepts else []
            self._last_trigger_cycle[stat_name] = self._cycle

            if not evoked:
                # there is no real memory to bring up -- nothing is invented.
                # it is flagged so the output layer can verbalize it
                # ("I'm scared, could you hold me?") -- pending.
                self.last_unmet_needs.append(stat_name)
                continue

            best = max(evoked, key=lambda e: e.get("mental_peak", 0.0))
            er_rr, p_a = best.get("graph", {}).get("peak_sign_mental", (0.0, 0.0))
            magnitude  = min(1.0, deficit)  # more lack -> slightly stronger echo, capped at 1.0

            self._echo_level[stat_name] = magnitude
            self._echo_vec[stat_name] = {
                "P":  magnitude if p_a  >= 0 else 0.0,
                "A":  0.0       if p_a  >= 0 else magnitude,
                "Er": magnitude if er_rr >= 0 else 0.0,
                "Rr": 0.0       if er_rr >= 0 else magnitude,
            }

        result = {k: 0.0 for k in MENTAL_KEYS}
        for stat_name, level in self._echo_level.items():
            vec = self._echo_vec[stat_name]
            for k in MENTAL_KEYS:
                result[k] += vec[k] * level * ECHO_SCALE
        return result


def process(evocation_push: dict) -> dict:
    """
    evocation_push : {P,A,Er,Rr} vector from MentalEvocation.tick() for this cycle.
    (chem_m -- MentalStateSystem -- was ALREADY applied in PING 2, it is not forwarded here.)
    """
    result = {k: evocation_push.get(k, 0.0) for k in MENTAL_KEYS}
    result["_pipeline"] = "internal_mental"
    result["_active"]   = [k for k in MENTAL_KEYS if result[k] != 0.0]
    return result
