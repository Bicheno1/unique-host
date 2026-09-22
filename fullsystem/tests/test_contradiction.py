# tests/test_contradiction.py — regression test for the "only what is clearly impossible" rule.
# Usage (from the project root):  python tests/test_contradiction.py
import os, sys, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from contradiction_cases import all_normal, ABSURD
from motors.cycle_manager_v5 import CycleManagerV5
from db import db_concepts
from core.pre_input import detect_contradiction

_ccm = CycleManagerV5()

def flagged(text):
    st = _ccm.process(text=text)
    return bool(detect_contradiction(st["concepts"], db_concepts.CONCEPTS, raw_text=text).get("is_contradiction"))

def test_no_false_positives_on_normal_sentences():
    fp = [t for t, _ in all_normal() if flagged(t)]
    assert not fp, f"{len(fp)} falsos positivos: {fp}"

def test_detects_clear_impossibilities():
    hits = [t for t in ABSURD if flagged(t)]
    # 17/20 measured on ; the 3 that are missing have a known cause
    # (dog/cat -> concept 'pet'; trout -> the lexicon has it as food).
    assert len(hits) >= 17, f"solo {len(hits)}/{len(ABSURD)} detectadas"

def test_explicit_cases():
    assert flagged("the cow flies across the field")
    assert not flagged("a bird flies over the wall")         # explicit related
    assert not flagged("the dragon flies over the village")   # fantasy exemption
    assert not flagged("the bat flies out of the cave")       # bat
    assert not flagged("dogs don't fly")                      # negada
    assert not flagged("can a cow fly?")                      # question
    assert not flagged("the sword sings a song to the king")  # figurative

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
