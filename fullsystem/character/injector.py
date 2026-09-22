# character/injector.py — UNIQUE HOST
#
# Takes a character.json (produced by questionnaire.build_character_json,
# or hand-edited) and:
#   1. Overwrites motors.core_identity.CORE_RULES
#   2. Merges concepts_seed into db.db_concepts.CONCEPTS
#   3. Sets base/current state (Fortitude) on a fresh CycleManagerV5
#   4. Patches saturation thresholds on systems.memory_system
#
# TODO: once the real question set / formulas are supplied,
# double check the threshold-patching approach below still matches how
# saturation is actually read elsewhere in the codebase.

import copy

import motors.core_identity as core_identity
import db.db_concepts as db_concepts
import db.db_somatic as db_somatic
import db.db_mental as db_mental
import systems.memory_system as memory_system


# ── Pristine copy of everything inject_character() mutates ───────────
# inject_character() writes into MODULE-LEVEL dicts (CONCEPTS, the tag
# tables, CORE_RULES, memory thresholds). Without a reset, loading a second
# character in the same process (Gradio: load Delia, then load Joaquin)
# would leave the first one's data mixed into the second. So the first call
# takes a snapshot of the untouched state and every call restores it first.
# Restoration is done IN PLACE (clear + update) because other modules hold
# references to these same dict objects.
_BASELINE = None


def _snapshot_baseline():
    global _BASELINE
    if _BASELINE is None:
        _BASELINE = {
            "concepts": copy.deepcopy(db_concepts.CONCEPTS),
            "tags_somatic": copy.deepcopy(db_somatic.TAG_VALUES_SOMATIC),
            "tags_mental": copy.deepcopy(db_mental.TAG_VALUES_MENTAL),
            "core_rules": copy.deepcopy(core_identity.CORE_RULES),
            "mental_high": memory_system.HIGH_MENTAL_THRESHOLD,
            "somatic_high": memory_system.HIGH_SOMATIC_THRESHOLD,
        }


def _restore_baseline():
    b = _BASELINE
    for target, key in ((db_concepts.CONCEPTS, "concepts"),
                        (db_somatic.TAG_VALUES_SOMATIC, "tags_somatic"),
                        (db_mental.TAG_VALUES_MENTAL, "tags_mental"),
                        (core_identity.CORE_RULES, "core_rules")):
        target.clear()
        target.update(copy.deepcopy(b[key]))
    memory_system.HIGH_MENTAL_THRESHOLD = b["mental_high"]
    memory_system.HIGH_SOMATIC_THRESHOLD = b["somatic_high"]


def inject_character(character_data: dict):
    """
    Applies a character.json dict to the module-level databases and
    returns a freshly instantiated, character-shaped CycleManagerV5.
    """
    from motors.cycle_manager_v5 import CycleManagerV5

    _snapshot_baseline()
    _restore_baseline()

    # ── 1. Core Identity rules ──────────────────────────────────
    rules = character_data.get("core_identity_rules", {})
    if rules:
        core_identity.CORE_RULES.clear()
        core_identity.CORE_RULES.update(rules)

    # ── 2a. Dynamic tag values (valencia, character/valence.py) ──
    # MUST run before 2b: concepts_seed below points its "related" at
    # these per-character tag names (e.g. "valence__family"), so the
    # tags need to exist in TAG_VALUES_SOMATIC/MENTAL first, or
    # pre_input's _concept_value() would silently find nothing for them.
    tag_seed = character_data.get("tag_values_seed", {})
    for tag, vec in tag_seed.get("somatic", {}).items():
        db_somatic.TAG_VALUES_SOMATIC[tag] = vec
    for tag, vec in tag_seed.get("mental", {}).items():
        db_mental.TAG_VALUES_MENTAL[tag] = vec

    # ── 2b. ConceptsDB seed ───────────────────────────────────────
    # A seed node never replaces a hand-authored base concept of type
    # "language" (father, mother, pet, be, angry, urgent...). Those carry the
    # grammar/identity contract of the engine; replacing them made
    # "who is your father?" answer "I am <name>" and turned "be" into an
    # emotional action (found in the smoke test,
    # 5.B-2). Everything else in the seed still overrides the base.
    seed = character_data.get("concepts_seed", {})
    for name, node in seed.items():
        base = db_concepts.CONCEPTS.get(name)
        if base is not None and base.get("type") == "language":
            continue
        if base is not None and base.get("related"):
            # MERGE instead of replace when the engine already has a hand-authored (or
            # db/db_danger.py) emotional push for the word. Before, the seed replaced it, so "bandit"
            # lost its danger tags and kept only the character's opinion of "people" (a bandit with a
            # drawn blade was welcomed). Base type/subtype/synonyms stay; the base groups win on a name
            # clash; the character's valence groups are added on top.
            merged = dict(base)
            merged["related"] = {**node.get("related", {}), **base["related"]}
            db_concepts.CONCEPTS[name] = merged
            continue
        db_concepts.CONCEPTS[name] = node

    # ── 3. Saturation thresholds (module-level patch) ───────────
    thresholds = character_data.get("saturation_thresholds", {})
    if "mental_high" in thresholds:
        memory_system.HIGH_MENTAL_THRESHOLD = float(thresholds["mental_high"])
    if "somatic_high" in thresholds:
        memory_system.HIGH_SOMATIC_THRESHOLD = float(thresholds["somatic_high"])

    # ── 4. Instantiate CCM and set base/current state (Fortitude) ─
    ccm = CycleManagerV5()
    ccm.identity_anchor_system.set_anchors(character_data.get("identity_anchors", []))

    # Character name -- used by core/construction_matcher.py to
    # normalize the input before parsing.
    identity = character_data.get("identity", {})
    ccm.character_name = identity.get("name")

    # Chemical system gain matrix (16 values, one per response-matrix cell).
    # Comes from QUESTIONS_PRIMARY_CHEMISTRY in the questionnaire (Category
    # Bias + Axis Gain). If not present, ChemicalSystem's DEFAULT_GAINS
    # (all neutral) let the raw push decide the winning mode, unchanged.
    chemical_gains = character_data.get("chemical_gains")
    if chemical_gains:
        ccm.chemicals.gains = chemical_gains

    # Primary Evaluator category bias (4 questions — separate layer from
    # the 16 chemical gains, see core/response_matrix.py). Same pattern:
    # apply if present, otherwise ChemicalSystem/CycleManagerV5 defaults
    # (all neutral) leave category selection exactly as pure geometry.
    category_bias = character_data.get("category_bias")
    if category_bias:
        ccm.category_bias = category_bias

    # Mental twin — same pattern as above, for
    # mental_states.release_from_axis_push. See the compiler package:
    # questionnaire/questionnaire.py block QUESTIONS_PRIMARY_MENTAL_CHEMISTRY.
    mental_gains = character_data.get("mental_gains")
    if mental_gains:
        ccm.mental_states.mental_gains = mental_gains

    mental_category_bias = character_data.get("mental_category_bias")
    if mental_category_bias:
        ccm.mental_category_bias = mental_category_bias

    base_state = character_data.get("base_state", {})

    s_base = base_state.get("somatic")
    if s_base:
        ccm.somatic.base    = dict(s_base)
        ccm.somatic.current = dict(s_base)
        ccm.somatic.external = dict(s_base)

    m_base = base_state.get("mental")
    if m_base:
        ccm.mental.base    = dict(m_base)
        ccm.mental.current = dict(m_base)
        ccm.mental.external = dict(m_base)

    # ── 5. Seed nuclear memories from "core" questionnaire answers ──
    # PROTOTYPE ( character/memory_seed.py) — turns core_fear/
    # core_comfort into synthetic events with the same shape
    # MemorySystem._close_event produces live, appended directly to
    # .long_term. MUST run after step 3 (saturation thresholds already
    # patched onto systems.memory_system) so the seeded events are
    # measured against THIS character's own thresholds, not the global
    # default -- memory_seed.py reads them off the module at call time.
    from character.memory_seed import seed_memory_from_character
    for event in seed_memory_from_character(character_data):
        ccm.memory_s.long_term.append(event)
        ccm.memory_m.long_term.append(event)

    return ccm, identity
