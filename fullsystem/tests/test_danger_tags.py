# tests/test_danger_tags.py — intrinsic danger tags (db/db_danger.py) + seed merge in the injector
# Run: python tests/test_danger_tags.py
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "displayer"))
from db.db_concepts import CONCEPTS
from db.db_danger import TEMPLATES, DANGER_WORDS
from db.db_somatic import TAG_VALUES_SOMATIC
from db.db_mental import TAG_VALUES_MENTAL


def _pristine():
    """Other tests inject characters (module-level dicts); go back to the untouched engine."""
    import character.injector as inj
    if inj._BASELINE is not None:
        inj._restore_baseline()


def test_every_template_tag_exists_in_the_tag_tables():
    for name, related in TEMPLATES.items():
        for group, branches in related.items():
            for t in branches["somatic"]:
                assert t in TAG_VALUES_SOMATIC, (name, group, t)
            for t in branches["mental"]:
                assert t in TAG_VALUES_MENTAL, (name, group, t)


def test_all_listed_words_and_their_inflections_carry_the_tags():
    for template, words in DANGER_WORDS.items():
        for w in words:
            node = CONCEPTS.get(w)
            assert node and node.get("related"), (template, w)
    for form in ("kills", "killed", "killing", "monsters", "burns", "burned", "collapses", "flames", "wounded", "lunges"):
        assert CONCEPTS[form]["related"], form
        assert CONCEPTS[form].get("intrinsic_danger"), form


def test_hand_authored_concepts_are_not_overwritten():
    assert "isolated" in CONCEPTS["alone"]["related"] and "intrinsic_danger" not in CONCEPTS["alone"]
    assert "paralysis" in CONCEPTS["scared"]["related"]["defenseless"]["somatic"] if "defenseless" in CONCEPTS["scared"]["related"] else True
    assert CONCEPTS["ghost"]["related"]["fear"]["somatic"] == ["adrenaline", "cortisol"]


def test_ordinary_words_stay_neutral():
    _pristine()
    from db.db_concepts import resolve_concept
    for w in ("breeze", "sings", "rests", "library", "hearts"):
        c = resolve_concept(w)
        assert not (CONCEPTS.get(c, {}).get("related")), w
    assert "beat" not in DANGER_WORDS["violence"]


def test_danger_words_push_inviability_and_absence_in_the_base_engine():
    _pristine()
    from core.pre_input import pre_input_somatic, pre_input_mental
    for w in ("monster", "kill", "blood", "fire", "blade", "cage", "wounded", "terror"):
        s = pre_input_somatic([w])
        assert s and s["I"] > s["V"], (w, s)
        if w != "blade":                       # a weapon is a physical threat; its mental tags are only alertness
            m = pre_input_mental([w])
            assert m and m["A"] > m["P"], (w, m)


def test_character_seed_is_merged_not_replaced():
    from character.injector import inject_character
    ch = json.load(open(os.path.join(HERE, "..", "..", "fullcompiler", "characters", "delia_adventurer_v4.json")))
    ccm, _ = inject_character(ch)
    bandit = CONCEPTS["bandit"]
    assert "fear" in bandit["related"] and "threat" in bandit["related"], bandit["related"].keys()     # hand-authored survives
    assert "valence" in bandit["related"], "the character's own valence is layered on top"
    assert bandit["type"] == "subject" and bandit["subtype"] == "person"                              # base type wins
    assert "threat" in CONCEPTS["monster"]["related"] and "valence" in CONCEPTS["monster"]["related"]
    # a second load starts from the pristine engine again (nothing of Delia's seed leaks)
    ch2 = json.load(open(os.path.join(HERE, "..", "..", "fullcompiler", "characters", "joaquin_adventurer_v2.json")))
    inject_character(ch2)
    assert CONCEPTS["monster"]["related"]["valence"]["somatic"] == ["valence__monster"]


def _play(ccm, turns):
    from core.marker_parser import parse_marked_input as P
    return [ccm.process(text="", marked_input=P(t)) for t in turns]


def _threat_events(ccm):
    m = ccm.memory_m
    return [e for e in m.short_term + m.medium_term + m.long_term if e.get("source") == "threat"]


def test_real_scenes_are_stored_and_recalled_for_delia_v4():
    from character.injector import inject_character
    ch = json.load(open(os.path.join(HERE, "..", "..", "fullcompiler", "characters", "delia_adventurer_v4.json")))
    scenes = {"bandit": ['<<a bandit lunges at her with a blade>>', '"Scared" <<the bandit strikes her>>', '<<she is wounded and afraid>>'],
              "monster": ['<<a monster kills her friend in front of her>>', '"Panicked" <<blood is everywhere>>'],
              "fire": ['<<a huge fire burns the library>>', '"Panicked" <<the roof collapses>>'],
              "cage": ['<<locks her in a cage>>', '<<the cage door slams shut>>']}
    calm = ['<<she sits and rests>>', '<<a warm breeze>>', 'Everything is quiet.', '<<birds sing>>']
    for word, turns in scenes.items():
        random.seed(5)
        ccm, _ = inject_character(ch)
        ccm.user_name = "Joaquin"
        _play(ccm, [calm[i % 4] for i in range(6)] + turns + [calm[i % 4] for i in range(6)])
        assert any(word in e["concepts"] for e in _threat_events(ccm)), (word, [e["concepts"] for e in _threat_events(ccm)])
        s = _play(ccm, [f"Do you remember the {word}?"])[0]
        assert s["recall"]["found"] and word in s["marked_output"], (word, s["marked_output"])


def test_no_false_events_in_60_calm_turns_for_both_characters():
    from character.injector import inject_character
    calm = ['<<she sits and rests>>', '<<a warm breeze>>', 'Everything is quiet.', '<<birds sing>>']
    for f in ("delia_adventurer_v4.json", "joaquin_adventurer_v2.json"):
        ch = json.load(open(os.path.join(HERE, "..", "..", "fullcompiler", "characters", f)))
        random.seed(5)
        ccm, _ = inject_character(ch)
        _play(ccm, [calm[i % 4] for i in range(60)])
        assert not _threat_events(ccm), (f, [e["concepts"] for e in _threat_events(ccm)])


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print("  OK  ", name)
        except Exception as e:
            failed += 1; print("  FAIL", name, "->", repr(e))
    print("\nTODO OK" if not failed else f"\n{failed} FAILED")
    sys.exit(1 if failed else 0)
