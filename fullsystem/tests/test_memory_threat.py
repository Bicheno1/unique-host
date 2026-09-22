# tests/test_memory_threat.py — events chosen by inviability / absence / danger (memory_system.py)
# Run: python tests/test_memory_threat.py
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import systems.memory_system as ms
from systems.memory_system import MemorySystem

REST_S = {"V": 5, "I": 5, "Lv": 5, "Gv": 5}
REST_M = {"P": 5, "A": 5, "Er": 5, "Rr": 5}
HIGH_S = {"V": 300, "I": 300, "Lv": 300, "Gv": 300}     # engine pinned high: distance says "nothing special"


def feed(mem, steps, s_state=REST_S, m_state=REST_M):
    """steps: list of (concepts, threat_s, threat_m)."""
    out = []
    for concepts, ts, tm in steps:
        e = mem.update("scene", concepts, s_state, m_state, ts, tm)
        if e: out.append(e)
    return out


def all_events(mem):
    return mem.short_term + mem.medium_term + mem.long_term


def test_threat_episode_becomes_one_negative_event():
    m = MemorySystem()
    feed(m, [(["sits"], 0, 0), (["cage", "lock"], 224, 145), (["cage"], 327, 123), (["door"], 0, 0), (["rest"], 0, 0)])
    ev = all_events(m)
    assert len(ev) == 1, ev
    e = ev[0]
    assert e["valence"] == "negative" and e["source"] == "threat" and "cage" in e["concepts"], e
    assert e["event_class"] in ("large", "major") and "rest" not in e["concepts"]


def test_closes_even_if_the_engine_never_returns_to_rest():
    m = MemorySystem()
    feed(m, [(["ghost"], 117, 74), (["ghost"], 100, 60), (["dark"], 0, 0), (["room"], 0, 0)], s_state=HIGH_S)
    assert len(all_events(m)) == 1


def test_needs_two_quiet_cycles_and_short_gaps_do_not_split():
    m = MemorySystem()
    feed(m, [(["monster"], 200, 0), (["a"], 0, 0), (["monster"], 200, 0), (["b"], 0, 0)])
    assert len(all_events(m)) == 0                       # still open (only 1 quiet cycle)
    feed(m, [(["c"], 0, 0)])
    assert len(all_events(m)) == 1 and "monster" in all_events(m)[0]["concepts"]


def test_below_threshold_and_pleasant_inputs_create_no_threat_event():
    m = MemorySystem()
    feed(m, [(["breeze"], 30, 15), (["birds"], 0, 0), (["sing"], 0, 0)] * 3)
    assert not any(e.get("source") == "threat" for e in all_events(m))


def test_axis_signal_is_normalised_per_engine():
    m = MemorySystem()
    feed(m, [(["loss"], 0, 40), (["loss"], 0, 40), (["x"], 0, 0), (["y"], 0, 0)])     # mental 40/200 = 0.20
    assert len(all_events(m)) == 1
    m = MemorySystem()
    feed(m, [(["loss"], 30, 0), (["loss"], 30, 0), (["x"], 0, 0), (["y"], 0, 0)])     # somatic 30/400 = 0.075
    assert len(all_events(m)) == 0


def test_repetition_escalates_threat_events_like_any_other():
    m = MemorySystem()
    for i in range(3):
        feed(m, [(["monster", "forest"], 200, 100), (["monster"], 200, 100), (["q"], 0, 0), (["q"], 0, 0)])
    assert len(m.medium_term) == 1 and m.medium_term[0]["source"] == "threat"


def test_no_double_count_with_the_distance_tracker():
    m = MemorySystem()
    big_s = {"V": 40, "I": 300, "Lv": 300, "Gv": 5}
    steps = [(["ghost"], 200, 100), (["ghost"], 200, 100), (["dark"], 0, 0), (["dark"], 0, 0)]
    for concepts, ts, tm in steps:
        m.update("scene", concepts, big_s, {"P": 5, "A": 150, "Er": 100, "Rr": 5}, ts, tm)
    for _ in range(4):
        m.update("scene", ["dark"], REST_S, REST_M)      # distance tracker now sees rest and would close
    assert len([e for e in all_events(m) if "ghost" in e["concepts"]]) == 1


def test_flag_off_is_the_old_behaviour():
    old = ms.THREAT_EVENTS_ENABLED
    ms.THREAT_EVENTS_ENABLED = False
    try:
        m = MemorySystem()
        feed(m, [(["cage"], 300, 145), (["cage"], 300, 145), (["x"], 0, 0), (["y"], 0, 0)])
        assert not any(e.get("source") == "threat" for e in all_events(m))
    finally:
        ms.THREAT_EVENTS_ENABLED = old


def test_threat_events_work_with_recall_and_claims():
    from test_memory_recall import new_ccm
    from core.memory_recall import build_recall
    c = new_ccm(user=None)
    feed(c.memory_m, [(["ghost", "room"], 117, 74), (["ghost"], 100, 60), (["x"], 0, 0), (["y"], 0, 0)])
    feed(c.memory_s, [(["ghost", "room"], 117, 74), (["ghost"], 100, 60), (["x"], 0, 0), (["y"], 0, 0)])
    r = build_recall(c, "Do you remember the ghost?", ["ghost"])
    assert r["found"] and "ghost" in r["phrase"]
    assert any(f in r["phrase"] for k in (("negative", False), ("negative", True)) for f in
               __import__("core.memory_recall", fromlist=["_FEELING"])._FEELING[k])


def test_an_episode_still_in_progress_can_already_be_recalled():
    from test_memory_recall import new_ccm
    from core.memory_recall import build_recall
    c = new_ccm(user=None)
    for mem in (c.memory_m, c.memory_s):
        feed(mem, [(["monster", "horse"], 200, 100), (["blood"], 150, 90), (["breath"], 0, 0)])   # 1 quiet cycle: still open
        assert mem._thr_active
    r = build_recall(c, "Do you remember the monster?", ["monster"])
    assert r["found"] and "monster" in r["phrase"] and "just now" in r["phrase"], r
    assert len(all_events(c.memory_m)) == 0                                    # nothing stored yet, only recalled
    for mem in (c.memory_m, c.memory_s):
        feed(mem, [(["breeze"], 0, 0)])                                          # 2nd quiet cycle: closes
    assert len(all_events(c.memory_m)) == 1
    r2 = build_recall(c, "Do you remember the monster?", ["monster"])
    assert r2["found"] and not c.memory_m._thr_active


def test_engine_stores_a_cage_episode_for_a_real_character():
    here = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(here, "..", "..", "displayer"))
    sys.path.insert(0, os.path.join(here, "..", "..", "fullcompiler"))
    from character.injector import inject_character
    from questionnaire.questionnaire import build_character_json
    from core.marker_parser import parse_marked_input as P
    a = json.load(open(os.path.join(here, "..", "..", "fullcompiler", "characters", "delia_answers_v4.json")))
    ch = build_character_json(dict(a, core_fear="cage", core_comfort="road"))
    random.seed(5)
    ccm, _ = inject_character(ch)
    for t in ['<<she sits and rests>>', '<<a warm breeze>>', '<<locks her in a cage>>', '<<the cage door slams shut>>',
              '<<she is trapped in the cage>>', '<<birds sing>>', 'Everything is quiet.', '<<she rests>>']:
        ccm.process(text="", marked_input=P(t))
    real = [e for e in all_events(ccm.memory_m) if e.get("source") == "threat"]
    assert len(real) == 1 and "cage" in real[0]["concepts"], real
    s = ccm.process(text="", marked_input=P("Do you remember the cage?"))
    assert s["recall"]["found"] and "cage" in s["marked_output"]


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
