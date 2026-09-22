# Run from the fullcompiler/ folder:  python test_compiler.py
from questionnaire.questionnaire import build_character_json, QUESTIONS
from questionnaire.completeness import check_completeness

full = {k: (7 if t == "slider" else "") for k, l, t, e in QUESTIONS}
full.update(name="Delia", age=27, core_fear="cage", purpose_source="freedom")

def test_builds_and_has_all_keys():
    c = build_character_json(full)
    for k in ("identity", "base_state", "category_bias", "chemical_gains",
              "mental_category_bias", "mental_gains", "concepts_seed",
              "tag_values_seed", "identity_anchors", "saturation_thresholds"):
        assert k in c, k
    assert len(c["concepts_seed"]) > 1000

def test_empty_answers_still_build():
    assert build_character_json({})["identity"]["name"] == "Unnamed"

def test_complete_form_no_warnings():
    assert check_completeness(full)["ok"]

def test_empty_form_warns_every_section():
    r = check_completeness({})
    assert not r["ok"] and len(r["warnings"]) >= 5

def test_partial_tree_counts_words():
    a = dict(full)
    for k, *_ in QUESTIONS:
        if k.startswith("tree__"): a[k] = 5
    a["tree__biological__animal"] = 9
    r = check_completeness(a)
    assert any("Likes tree" in w and "words" in w for w in r["warnings"]), r["warnings"]

def test_phrase_in_free_text_is_flagged():
    a = dict(full, core_fear="being caged")
    assert any("core_fear" in w for w in check_completeness(a)["warnings"])

def test_new_tree_branches_exist_and_coverage():
    from questionnaire.tree_questionnaire import TREE_QUESTIONS
    from lexicon_db.db_lexicon import LEXICON
    from lexicon_db.db_category_words import CATEGORY_WORDS
    keys = {q[0] for q in TREE_QUESTIONS}
    for k in ("tree__non_biological__violence_crime", "tree__non_biological__warm_emotions",
              "tree__non_biological__freedom", "tree__biological__crowds_groups"):
        assert k in keys, k
    covered = {w for ws in CATEGORY_WORDS.values() for w in ws} & set(LEXICON)
    assert len(covered) >= 6000, len(covered)

def test_none_and_blank_values_do_not_crash():
    c = build_character_json({"fort_V": None, "fort_P": "", "fort_I": "abc", "bias_danger": float("nan"),
                              "age": None, "name": None, "core_fear": None})
    assert c["base_state"]["somatic"]["V"] == 25.0          # default 5 -> 25
    assert c["identity"]["age"] == 25 and c["identity"]["name"] == "Unnamed"

def test_string_numbers_are_accepted():
    assert build_character_json({"fort_V": "8"})["base_state"]["somatic"]["V"] == 40.0

def test_out_of_range_is_clamped():
    c = build_character_json({"fort_V": 99, "bias_danger": -3, "age": -5, "height_cm": 0})
    assert c["base_state"]["somatic"]["V"] == 50.0
    assert c["category_bias"]["danger"] == 1.0
    assert c["identity"]["age"] == 1 and c["identity"]["height"] == "50cm"

def test_blank_name_becomes_unnamed():
    assert build_character_json({"name": "   "})["identity"]["name"] == "Unnamed"

def test_core_fear_keeps_existing_concept_type():
    import lexicon_db.db_concepts as dbc
    orig = dbc.CONCEPTS["ghost"]["type"]
    assert build_character_json({"core_fear": "ghost"})["concepts_seed"]["ghost"]["type"] == orig
    # a new word still uses "subject"
    assert build_character_json({"core_fear": "zzznewword"})["concepts_seed"]["zzznewword"]["type"] == "subject"

def test_input_dict_is_not_mutated():
    a = {"fort_V": None, "name": " x "}
    build_character_json(a)
    assert a == {"fort_V": None, "name": " x "}

def test_no_spanish_or_proper_names_left():
    import lexicon_db.db_concepts as dc
    from questionnaire.questionnaire import WORLD_GROUPS
    SP = {"cuarto","habitacion","oscuro","luz","iluminado","noche","bosque","hogar","lugar","calle",
          "avenida","afuera","comida","agua","dinero","llave","puerta","ventana","melodia","cancion",
          "musica","peces","pez","pescado","tiburon","trucha","pato","patos","sombra","cadaver",
          "muerto","alarido","grito","murmullo","familia","julia","angelo"}
    for k, v in dc.CONCEPTS.items():
        for s in v.get("synonyms", []):
            assert s not in SP and not s.endswith("_es"), (k, s)
    for g in WORLD_GROUPS.values():
        for name, _sense, _sub, syn in g["words"]:
            for s in [name] + syn:
                assert s not in SP and not s.endswith("_es"), (name, s)
    assert "casa" not in dc.CONCEPTS and "llaves" not in dc.CONCEPTS and "angelo" not in dc.CONCEPTS

def test_house_and_key_replace_casa_and_llaves():
    c = build_character_json({"environment_opinion": 8, "world_objects_opinion": 3})
    assert "house" in c["concepts_seed"] and "key" in c["concepts_seed"]
    assert "casa" not in c["concepts_seed"] and "llaves" not in c["concepts_seed"]
    assert "safe" in c["concepts_seed"]["house"]["related"]     # the relations of "casa" were preserved

def test_names_are_not_seeded_by_default():
    c = build_character_json({})
    assert not any(n in c["concepts_seed"] for n in ("angelo", "tobi", "juan", "julia"))

def test_delia_golden_and_extras():
    """Delia's answers compile EXACTLY to the saved v3, and keep her v2 identity."""
    import json, os
    here = os.path.dirname(os.path.abspath(__file__))
    answers = json.load(open(os.path.join(here, "characters", "delia_answers.json"), encoding="utf-8"))
    v3 = json.load(open(os.path.join(here, "characters", "delia_adventurer_v3.json"), encoding="utf-8"))
    v2 = json.load(open(os.path.join(here, "characters", "delia_adventurer_v2.json"), encoding="utf-8"))
    assert json.loads(json.dumps(build_character_json(answers))) == v3
    assert v3["core_identity_rules"] == v2["core_identity_rules"]       # parents, pet, custom_friend, fear, comfort
    for k in ("identity", "base_state", "category_bias", "chemical_gains", "saturation_thresholds"):
        assert v3[k] == v2[k], k

def test_family_and_friend_fields_only_when_given():
    c = build_character_json({})
    assert "custom_friend" not in c["core_identity_rules"]
    assert "father" not in c["core_identity_rules"]["host_identity"]["value"]
    c = build_character_json({"father_name": "Tomás", "friend_name": "Joaquin"})
    assert c["core_identity_rules"]["host_identity"]["value"]["father"] == "Tomás"
    assert c["core_identity_rules"]["custom_friend"]["value"] == {"name": "Joaquin", "role": "friend"}
    assert "joaquin" not in c["concepts_seed"]           # names are NOT seeded as concepts

def test_joaquin_golden_all_questions_answered():
    import json, os
    from questionnaire.completeness import check_completeness
    here = os.path.dirname(os.path.abspath(__file__))
    answers = json.load(open(os.path.join(here, "characters", "joaquin_answers.json"), encoding="utf-8"))
    saved = json.load(open(os.path.join(here, "characters", "joaquin_adventurer_v1.json"), encoding="utf-8"))
    assert check_completeness(answers)["ok"]                      # all 166 questions answered, no phrases
    assert json.loads(json.dumps(build_character_json(answers))) == saved
    assert saved["core_identity_rules"]["custom_friend"]["value"]["name"] == "Delia"

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK ", n)
