# tests/test_memory_tiers.py — short -> medium -> long escalation by repetition
# Run: python tests/test_memory_tiers.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_memory_recall import new_ccm, live_event, REST_S, REST_M
import systems.memory_system as ms


def sizes(c):
    m = c.memory_m
    return len(m.short_term), len(m.medium_term), len(m.long_term)


def test_short_to_medium_at_3_reps():
    c = new_ccm(user=None)
    live_event(c, ["monster", "forest"]); live_event(c, ["monster", "forest"])
    assert sizes(c) == (1, 0, 0)
    live_event(c, ["monster", "forest"])
    assert sizes(c) == (1, 1, 0) and c.memory_m.medium_term[0]["reps"] == 3


def test_medium_to_long_at_10_reps_once():
    c = new_ccm(user=None)
    for i in range(1, 10):
        live_event(c, ["monster", "forest"])
    assert sizes(c)[2] == 0 and c.memory_m.medium_term[0]["reps"] == 9   # medium keeps counting now
    live_event(c, ["monster", "forest"])
    assert sizes(c)[1:] == (0, 1), sizes(c)          # promoted: medium emptied, one long entry
    assert c.memory_m.long_term[0]["reps"] >= 10
    for i in range(6):
        live_event(c, ["monster", "forest"])          # more repeats: no duplicates
    assert sizes(c)[1:] == (0, 1) and c.memory_m.long_term[0]["reps"] >= 16, sizes(c)


def test_repeat_resets_medium_age():
    c = new_ccm(user=None)
    for i in range(3):
        live_event(c, ["monster", "forest"])
    c.memory_m.medium_term[0]["age"] = 90
    live_event(c, ["monster", "forest"])
    assert c.memory_m.medium_term[0]["age"] < 10          # reset to 0, then a few rest cycles of live_event


def test_unrepeated_short_term_expires():
    c = new_ccm(user=None)
    live_event(c, ["monster"])
    assert sizes(c)[0] == 1
    for i in range(ms.SHORT_TERM_AGE + 1):
        c.memory_m.update("idle", [], REST_S, REST_M)
    assert sizes(c) == (0, 0, 0)


def test_different_events_do_not_escalate_together():
    c = new_ccm(user=None)
    for i in range(3):
        live_event(c, ["monster", "forest"])
    for i in range(3):
        live_event(c, ["river", "boat"])
    m = c.memory_m
    assert sorted(tuple(sorted(e["concepts"])) for e in m.medium_term) == [("boat", "river"), ("forest", "monster")]


def test_seeded_long_term_memory_is_reinforced_not_duplicated():
    c = new_ccm(user=None)
    c.memory_m.long_term.append({"concepts": ["cage"], "event_class": "major", "is_nuclear": True,
                                 "mental_peak": 90, "somatic_peak": 200, "reps": 1, "valence": "negative",
                                 "closed_at": None, "graph": {}})
    for i in range(4):
        live_event(c, ["cage"])
    assert sizes(c)[2] == 1 and c.memory_m.long_term[0]["reps"] >= 2


def test_recall_finds_an_escalated_event_as_long_term():
    from core.memory_recall import build_recall
    c = new_ccm(user=None)
    for i in range(10):
        live_event(c, ["monster", "forest"])
    r = build_recall(c, "Do you remember the monster?", ["monster"])
    assert r["found"] and r["tier"] == "long" and "a long time ago" in r["phrase"], r


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
