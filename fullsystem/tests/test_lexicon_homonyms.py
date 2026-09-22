# tests/test_lexicon_homonyms.py — regression test for the homonym corrections.
# Usage (from the project root):  python tests/test_lexicon_homonyms.py
import os, sys, copy, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from db.db_lexicon import LEXICON
from db.db_lexicon_overrides import LEXICON_OVERRIDES, LEXICON_ADDITIONS, apply_overrides


def test_overrides_applied():
    for w, f in LEXICON_OVERRIDES.items():
        for k, v in f.items():
            assert LEXICON[w][k] == v, (w, k)
    for w in LEXICON_ADDITIONS:
        assert w in LEXICON, w


def test_blade_is_a_weapon_not_a_plant():
    e = LEXICON["blade"]
    assert (e["category"], e["node_type"], e.get("subtype")) == ("object", "non_biological", "weapon")


def test_subtype_dropped_when_override_has_none():
    # raven has no subtype: it must not inherit an old one from the wrong sense
    assert "subtype" not in LEXICON["raven"]


def test_idempotent():
    snap = copy.deepcopy(LEXICON)
    apply_overrides(LEXICON)
    assert snap == LEXICON


def test_untouched_entries_unchanged():
    # a word without an override stays the same (ambiguous ones are left for review)
    assert LEXICON["bolt"]["category"] == "weather"


def test_blade_drawn_no_false_contradiction():
    from core.pre_input import detect_contradiction
    from db import db_concepts
    from motors.cycle_manager_v5 import CycleManagerV5
    ccm = CycleManagerV5()
    t = "a bandit steps out of the bushes, blade drawn"
    st = ccm.process(text=t)
    info = detect_contradiction(st["concepts"], db_concepts.CONCEPTS, raw_text=t)
    assert info["is_contradiction"] is False, info


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  OK   {name}")
            except AssertionError as e:
                fails += 1; print(f"  FAIL {name}: {e}")
    print("\nTODO OK" if not fails else f"\n{fails} FALLO(S)")
    sys.exit(1 if fails else 0)
