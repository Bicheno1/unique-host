# tests/test_state_reset.py — inject_character() must leave NO trace of the previous character/session
# Run: python tests/test_state_reset.py
#
# Before: STAT_DATABASE (vitals: heart rate, energy, temperature...) and
# internal_somatic._threat_state["prev_dist"] were module-level and were not restored, so a second
# character loaded in the same process (Gradio) inherited the first one's body, and the same scene with
# the same seed could give a different intensity depending on what had run before.
import os, sys, json, random, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))

import systems.core_system as _cs
import motors.internal_somatic as _ins
# what the engine looks like before anything has run in this process
PRISTINE_STATS = copy.deepcopy(_cs.STAT_DATABASE)
PRISTINE_THREAT = copy.deepcopy(_ins._threat_state)

CHARS = os.path.join(HERE, "..", "..", "fullcompiler", "characters")
DELIA = "delia_adventurer_v4.json"
JOAQUIN = "joaquin_adventurer_v2.json"
SCENES = ['<<a bandit lunges at her with a blade>>', '"Scared" <<the bandit strikes her>>',
          '<<a monster kills the horse in front of her>>', '"Panicked" <<blood is everywhere>>',
          '<<she sits by the fire and rests>>', 'Everything is quiet.']


def _load(fname):
    return json.load(open(os.path.join(CHARS, fname), encoding="utf-8"))


def _play(fname, seed=3, turns=SCENES):
    """Fresh character, fixed seed; returns the visible text of every reply."""
    from character.injector import inject_character
    from core.marker_parser import parse_marked_input as P
    random.seed(seed)
    ccm, _ = inject_character(_load(fname))
    ccm.user_name = "Joaquin"
    return [ccm.process(text="", marked_input=P(t))["marked_output"] for t in turns]


def test_stat_database_and_threat_state_are_restored_on_every_load():
    import systems.core_system as cs
    import motors.internal_somatic as ins
    from character.injector import inject_character
    _play(DELIA)                                   # play a whole scene set (heart rate goes to ~180)...
    assert cs.STAT_DATABASE["heart_rate"]["value"] != PRISTINE_STATS["heart_rate"]["value"], "scenes did not move the body"
    inject_character(_load(JOAQUIN))               # ...then load another character
    assert cs.STAT_DATABASE == PRISTINE_STATS, "vitals leaked from the previous session"
    assert ins._threat_state == PRISTINE_THREAT, ins._threat_state


def test_restore_is_in_place_so_other_modules_keep_seeing_the_same_dict():
    import systems.core_system as cs
    import motors.internal_somatic as ins
    from motors.internal_somatic import STAT_DATABASE as seen_by_somatic
    from character.injector import inject_character
    stat_id, threat_id = id(cs.STAT_DATABASE), id(ins._threat_state)
    inject_character(_load(DELIA))
    assert id(cs.STAT_DATABASE) == stat_id and cs.STAT_DATABASE is seen_by_somatic
    assert id(ins._threat_state) == threat_id


def test_same_scene_and_seed_gives_the_same_replies_whatever_ran_before():
    alone = _play(DELIA)
    _play(JOAQUIN, seed=9)                         # noise: another character, another seed
    _play(DELIA, seed=1, turns=SCENES[:3])         # noise: half a session
    again = _play(DELIA)
    assert alone == again, list(zip(alone, again))


def test_second_character_does_not_inherit_the_first_ones_body():
    import systems.core_system as cs
    from character.injector import inject_character
    from core.marker_parser import parse_marked_input as P
    ccm, _ = inject_character(_load(DELIA))
    random.seed(3)
    for t in SCENES[:4]:                           # Delia is scared: her heart rate moves
        ccm.process(text="", marked_input=P(t))
    assert cs.STAT_DATABASE["heart_rate"]["value"] != PRISTINE_STATS["heart_rate"]["value"]
    inject_character(_load(JOAQUIN))               # a new character starts from a rested body
    assert cs.STAT_DATABASE["heart_rate"]["value"] == PRISTINE_STATS["heart_rate"]["value"]


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
