# tests/test_chemical_depletion.py — release reserve + saturation block (paper §4.9.1)
# Run: python tests/test_chemical_depletion.py
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import systems.chemical_system as cs

PUSH = {"V": 60.0, "I": 0.0, "Lv": 0.0, "Gv": 0.0}


def level_after(n_releases, enabled=True, somatic_dist=None):
    old = cs.DEPLETION_ENABLED
    cs.DEPLETION_ENABLED = enabled
    try:
        c = cs.ChemicalSystem()
        gained = []
        for _ in range(n_releases):
            before = sum(c.levels.values())
            c.release_from_axis_push("danger", PUSH, somatic_dist=somatic_dist)
            gained.append(sum(c.levels.values()) - before)
        return c, gained
    finally:
        cs.DEPLETION_ENABLED = old


def test_disabled_is_the_old_behaviour():
    c, gained = level_after(3, enabled=False)
    assert all(abs(g - 60.0 / 20.0) < 1e-9 or c.levels["attack"] >= 9.99 for g in gained), gained
    assert c._reserve == 1.0


def test_release_shrinks_as_the_reserve_drains():
    _, gained = level_after(4)
    assert gained[0] > gained[1] > gained[2] or gained[2] == 0.0, gained
    assert gained[0] > 2.5 and gained[-1] < gained[0] / 2, gained


def test_repeated_release_ends_below_the_undepleted_level():
    on, _ = level_after(6, enabled=True)
    off, _ = level_after(6, enabled=False)
    assert on.levels["attack"] < off.levels["attack"], (on.levels["attack"], off.levels["attack"])


def test_refractory_then_recovery():
    c, _ = level_after(3)                                   # burst empties the reserve
    assert c._reserve < 0.2
    fresh = cs.ChemicalSystem(); fresh.release_from_axis_push("danger", PUSH)
    c.levels = {k: 0.0 for k in c.levels}                   # level gone, reserve still low
    c.release_from_axis_push("danger", PUSH)
    assert c.levels["attack"] < fresh.levels["attack"] / 2  # weaker than normal: refractory
    for _ in range(int(1 / cs.RESERVE_REGEN_PER_CYCLE) + 2):
        c.decay()
    assert c._reserve == 1.0                                # slowly refilled


def test_saturation_blocks_release_but_keeps_the_label():
    c, gained = level_after(1, somatic_dist=100.0)          # "saturated" band
    assert sum(c.levels.values()) == 0.0 and c._reserve == 1.0
    ret = cs.ChemicalSystem().release_from_axis_push("danger", PUSH, somatic_dist=100.0)
    assert ret is not None and ret[0] == "V"                # winning axis still reported (emotion label)
    c2, _ = level_after(1, somatic_dist=30.0)               # "active": allowed
    assert c2.levels["attack"] > 0


def test_pushes_and_decay_unchanged():
    c = cs.ChemicalSystem(); c.levels["attack"] = 10.0
    assert abs(c.get_somatic_push()["V"] - 50.0) < 1e-9
    c.decay(); assert abs(c.levels["attack"] - 10.0 * 0.5 ** (1 / 2)) < 1e-9


def _engine_run(character, enabled):
    old = cs.DEPLETION_ENABLED
    cs.DEPLETION_ENABLED = enabled
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "displayer"))
        from character.injector import inject_character
        import systems.memory_system as ms
        from core.marker_parser import parse_marked_input as P
        random.seed(5)
        ccm, _ = inject_character(character)
        calm = ['<<she sits and rests>>', '<<a warm breeze>>', 'Everything is quiet.', '<<birds sing>>']
        for i in range(8):
            ccm.process(text="", marked_input=P(calm[i % 4]))
        peak = 0.0
        for t in ['<<a bandit lunges at her with a blade>>', '"Scared" <<the bandit strikes her>>', '<<she is wounded and afraid>>']:
            ccm.process(text="", marked_input=P(t)); peak = max(peak, ms._somatic_dist(ccm.somatic.current_state()))
        plateau = []
        for i in range(36):
            ccm.process(text="", marked_input=P(calm[i % 4]))
            if i >= 20:
                plateau.append(ms._somatic_dist(ccm.somatic.current_state()))
        return peak, sum(plateau) / len(plateau)
    finally:
        cs.DEPLETION_ENABLED = old


def test_engine_settles_lower_but_still_reacts():
    here = os.path.dirname(__file__)
    ch = json.load(open(os.path.join(here, "..", "..", "fullcompiler", "characters", "joaquin_adventurer_v2.json")))
    peak_on, plat_on = _engine_run(ch, True)
    peak_off, plat_off = _engine_run(ch, False)
    assert plat_on < plat_off * 0.75, (plat_on, plat_off)     # comes down further
    assert peak_on > peak_off * 0.6, (peak_on, peak_off)      # the scare still registers


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
