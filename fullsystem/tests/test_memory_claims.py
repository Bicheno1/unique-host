# tests/test_memory_claims.py — comparing what the user claims with stored events
# (core/memory_claims.py). Events go through the real MemorySystem.update() closing code.
# Run: python tests/test_memory_claims.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_memory_recall import new_ccm, live_event, concepts_of
from core.memory_claims import check_claim
from core.marker_parser import parse_marked_input
import core.memory_recall as mr


def claim(ccm, text):
    return check_claim(ccm, text, concepts_of(text))


def bad_monster():
    c = new_ccm(); live_event(c, ["monster"], good=False); return c


def good_monster():
    c = new_ccm(); live_event(c, ["monster"], good=True); return c


def test_question_confirmed():
    r = claim(bad_monster(), "Did you see the monster yesterday?")
    assert r and r["kind"] == "confirm" and r["phrase"].startswith("Yes.") and "monster" in r["phrase"], r


def test_question_about_feeling_confirmed_or_corrected():
    r = claim(bad_monster(), "Were you scared of the monster?")
    assert r["kind"] == "confirm" and r["stored"] == "negative" and r["claimed"] == "negative", r
    r = claim(good_monster(), "Were you scared of the monster?")
    assert r["kind"] == "contradiction" and r["phrase"].startswith(("No.", "Not really.")), r
    assert any(f in r["phrase"] for k in (("positive", False), ("positive", True)) for f in mr._FEELING[k]), r


def test_assertion_confirmed_and_contradicted():
    r = claim(bad_monster(), "The monster attacked you.")
    assert r["kind"] == "confirm" and r["phrase"].startswith("That's right."), r
    r = claim(bad_monster(), "You liked the monster.")
    assert r["kind"] == "contradiction" and r["stored"] == "negative" and r["claimed"] == "positive", r
    assert r["phrase"].startswith(("That's not how it was.", "No. That's not what I remember.")), r


def test_negation_flips_the_claim():
    r = claim(bad_monster(), "The monster didn't hurt you.")      # "not bad" = good, stored bad
    assert r["kind"] == "contradiction" and r["claimed"] == "positive", r
    r = claim(good_monster(), "The monster didn't hurt you.")     # matches
    assert r["kind"] == "confirm", r


def test_unknown_polarity_only_confirms():
    r = claim(bad_monster(), "Did the monster follow you yesterday?")
    assert r["kind"] == "confirm" and r["claimed"] is None, r


def test_nothing_stored_is_not_invented():
    c = bad_monster()
    r = claim(c, "Did you see the dragon?")
    assert r["kind"] == "unknown" and not r["found"] and "dragon" in r["phrase"], r
    assert claim(c, "The dragon attacked you.") is None            # undated assertion: not judged
    assert claim(c, "The dragon attacked you yesterday.")["phrase"] == "I don't remember that."


def test_claims_about_the_user():
    c = new_ccm(); live_event(c, ["joaquin", "camp"], good=True)
    r = claim(c, "Did I scare you?")
    assert r["kind"] == "contradiction" and r["subject"] == "joaquin", r
    c = new_ccm(); live_event(c, ["joaquin", "monster"], good=False)
    assert claim(c, "Did I scare you?")["kind"] == "confirm"


def test_not_a_claim():
    c = bad_monster()
    for t in ["Who are you?", "The monster attacks the camp.", "Did you eat?", "Watch out, a monster!",
              "You are brave.", "Do you remember the monster?", "What do you think about me?"]:
        assert claim(c, t) is None, t


def test_engine_puts_contradiction_in_its_own_channel():
    c = bad_monster()
    s = c.process(text="", marked_input=parse_marked_input("You liked the monster yesterday."))
    out = s["marked_output"]
    assert "That's not how it was" in out or "That's not what I remember" in out, out
    assert "<<remembering the monster>>" in out, out
    s = c.process(text="", marked_input=parse_marked_input("Did you see the monster?"))
    assert "Yes" in s["marked_output"], s["marked_output"]
    s = c.process(text="", marked_input=parse_marked_input("You are 40 years old"))      # identity check still first
    assert "<<remembering" not in s["marked_output"]


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
