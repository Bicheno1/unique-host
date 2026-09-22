# motors/core_identity.py — CCM v5
#
# CORE IDENTITY — permanent identity of the host
#
# RECEIVES: input vector (somatic or mental) + active concepts
# DOES:     consults CORE_RULES — amplifies or contains the vector
# OUTPUTS:  modified vector + active rules
#
# NEVER changes per tick. Only changes if the host experiences a nuclear event.
# Permanent personality layer: fears, beliefs, traumas, values.

from db.db_concepts import resolve_concept

CORE_RULES = {
    "host_identity": {
        "type":     "identity",
        "concepts": ["name", "identity", "self", "which", "who", "you", "julia"],
        "effect":   "none",
        "factor":   1.0,
        "value":    {"name": "Julia", "age": 28, "height": "163cm"},
        "note":     "Base identity of the host — replace with target agent",
    },
    "fear_of_ghosts": {
        "type":     "fear",
        "concepts": ["ghost", "shadow", "supernatural", "spirit", "phantom"],
        "effect":   "amplify",
        "factor":   2.0,
        "note":     "Saw a ghost as a child — maximum terror",
    },
    "darkness_danger": {
        "type":     "fear",
        "concepts": ["dark", "darkness", "night", "dark_sp"],
        "effect":   "amplify",
        "factor":   1.6,
        "note":     "Darkness triggers childhood memory",
    },
    "light_safety": {
        "type":     "relief",
        "concepts": ["light", "safe", "calm"],   # removed "person" — aggressive person does not provide relief
        "effect":   "contain",
        "factor":   0.4,
        "note":     "Light and calm reduce terror",
    },
    "threat_to_identity": {
        "type":     "defense",
        "concepts": ["aggressive", "threat", "danger"],
        "effect":   "guard_identity",
        "factor":   1.0,
        "note":     "Direct threat — protects identity, does not reveal name",
    },
}


def consult(concept_names: list) -> list:
    """Returns list of (rule_name, rule) for active concepts."""
    canonical = set()
    for c in concept_names:
        name = resolve_concept(c) or c
        canonical.add(name)
    active = []
    for rule_name, rule in CORE_RULES.items():
        if canonical & set(rule["concepts"]):
            active.append((rule_name, rule))
    return active


def apply(vector: dict, keys: list, active_rules: list) -> dict:
    """
    Receives vector + list of active rules.
    Returns the modified vector by amplification/containment factor.
    """
    if not active_rules:
        return vector
    from db.db_somatic import SOMATIC_MAX
    from db.db_mental  import MENTAL_MAX
    cap   = SOMATIC_MAX if any(k in keys for k in ("V", "I", "Lv", "Gv")) else MENTAL_MAX
    result = dict(vector)
    for rule_name, rule in active_rules:
        factor = rule["factor"]
        effect = rule["effect"]
        if effect == "amplify":
            for k in keys:
                if k in result and isinstance(result[k], float):
                    result[k] = min(result[k] * factor, float(cap))
        elif effect == "contain":
            for k in keys:
                if k in result and isinstance(result[k], float):
                    result[k] = result[k] * factor
    result["_core_rules"] = [r[0] for r in active_rules]
    return result


def apply_to_output(output: dict, active_rules: list, concept_names: list = None) -> dict:
    """Modifies the final output (tension, speed) based on active rules."""
    if not active_rules:
        return output

    concept_set = set(concept_names or [])

    for rule_name, rule in active_rules:
        effect = rule["effect"]
        factor = rule["factor"]

        if effect == "guard_identity":
            # direct threat + identity question → firm refusal
            if concept_set & {"name", "identity", "who", "you"}:
                output["verbal"]       = "i won't tell you!"
                output["core_applied"] = rule_name
            tension_map = {"low":"medium","medium":"high","high":"critical","critical":"critical"}
            output["movement"]["tension"]   = tension_map.get(
                output["movement"]["tension"], "high")
            output["movement"]["speed"] *= 1.2

        elif effect == "contain":
            tension_map = {"critical":"high","high":"medium","medium":"low","low":"low"}
            output["movement"]["tension"]   = tension_map.get(
                output["movement"]["tension"], "low")
            output["movement"]["speed"] *= 0.5
            output["core_applied"] = rule_name

        elif effect == "amplify":
            tension_map = {"low":"medium","medium":"high","high":"critical","critical":"critical"}
            output["movement"]["tension"]   = tension_map.get(
                output["movement"]["tension"], "high")
            output["movement"]["speed"] *= factor
            output["core_applied"] = rule_name

    return output


# ── IDENTITY ANCHORS ────────────────────────────────────────
#
# THE IDEA: purpose/security/company/structure do not
# decay on their own -- the character's narrative sustains them AS LONG AS it is not
# contradicted. Each anchor comes from the questionnaire (identity_anchors in
# character.json, see the compiler package's questionnaire/questionnaire.py): one
# concrete word ("family", "armed", "routine"...) tied to one of the
# 4 stats.
#
# Each cycle, per anchor:
#   - if its concept appears together with a loss/negation word
#     (THREAT_MARKERS) -- e.g. "family" + "dead" -- it is a direct ATTACK
#     on that part of the narrative: a strong push DOWN on its stat,
#     and it is left "shaken" (cooldown) before feeding again.
#   - if there is no attack, it feeds a little at a time (small, constant push) --
#     the concept does NOT need to appear in the scene to
#     feed; it is enough that it hasn't been contradicted. It is the
#     "continuity of the narrative" sustaining the stat, not a
#     one-off event.
#
# CEILING: the push uses the same _apply_delta bounded 0-10 that
# vital_system.py already uses for everything else -- it cannot grow without limit,
# same mechanism that keeps this from becoming a new Bug C.

THREAT_MARKERS = [
    "dead", "dying", "died", "gone", "lost", "killed", "destroyed",
    "broken", "betrayed", "fake", "false", "failed", "abandoned",
]

ANCHOR_FEED    = 0.06   # light push per cycle while it is not attacked
ANCHOR_SHATTER = 3.0    # strong downward push when it is attacked
SHAKEN_COOLDOWN = 8     # cycles without feed after an attack, before feeding again


class IdentityAnchorSystem:
    """Sustains or shakes purpose/security/company/structure depending on whether the
    character's narrative (its anchors) is still intact or was attacked
    this cycle."""

    def __init__(self, anchors: list = None):
        self.anchors = anchors or []          # [{"concept": str, "target_stat": str}, ...]
        self._shaken_until = {}               # concept -> cycle at which the cooldown ends
        self._cycle = 0

    def set_anchors(self, anchors: list):
        self.anchors = anchors or []

    def tick(self, concept_names: list, vitality):
        """
        concept_names : active concepts this cycle (already resolved)
        vitality      : instance of motors.vitality_stats.VitalityStats
        """
        self._cycle += 1
        if not self.anchors:
            return
        cs = set(concept_names or [])
        vs = vitality._vs

        for anchor in self.anchors:
            concept = anchor.get("concept")
            stat    = anchor.get("target_stat")
            if not concept or not stat:
                continue

            attacked = concept in cs and bool(cs & set(THREAT_MARKERS))
            if attacked:
                vs._apply_delta(stat, -ANCHOR_SHATTER)
                self._shaken_until[concept] = self._cycle + SHAKEN_COOLDOWN
                continue

            if self._shaken_until.get(concept, 0) > self._cycle:
                continue  # still shaken -- does not feed until the cooldown passes

            vs._apply_delta(stat, ANCHOR_FEED)
