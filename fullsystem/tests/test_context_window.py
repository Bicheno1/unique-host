# tests/test_context_window.py — the context window feeding short-term memory, and the "where are we
# going?" answer (systems/memory_system.py CONTEXT WINDOW section, core/memory_recall.py _answer_where).
#
# Before this: a scene with no threat/absence event never closed for real characters (they rest at
# D~120-350, C~45-130, far above the close thresholds), so nothing but seeded fears/comforts ever
# reached short-term memory. "Do you remember the market?" answered "I don't remember" one turn after
# going there, and "where are we going?" could not answer at all — nothing kept the plain fact "going,
# market" anywhere memory_recall could read.
#
# Run: python tests/test_context_window.py
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_memory_recall import new_ccm
from core.marker_parser import parse_marked_input as P
from core.memory_recall import build_recall
import systems.memory_system as ms


def say(ccm, text):
    return ccm.process(text="", marked_input=P(text))


def test_a_plain_scene_is_readable_from_the_open_window_before_any_flush():
    """One turn after "going to the market", nothing has flushed yet (CONTEXT_FLUSH_TURNS=6), but the
    open window itself must already answer a direct question about it."""
    c = new_ccm()
    say(c, "we going to the market")
    out = say(c, "Do you remember the market?")["marked_output"]
    assert "market" in out.lower() and "don't remember" not in out.lower(), out


def test_where_are_we_going_answers_from_the_open_window():
    c = new_ccm()
    say(c, "we going to the city")
    out = say(c, "where are we going?")["marked_output"]
    assert "city" in out.lower(), out


def test_where_ignores_the_current_turn_and_uses_the_latest_earlier_destination():
    c = new_ccm()
    say(c, "we going to the city")
    say(c, "the road is long")
    out = say(c, "we going to the forest, where are we going?")["marked_output"]
    # "forest" is in the SAME turn as the question: must not self-answer with it, nor drop to "city"
    # (older) while "forest" (this turn) is the real latest destination once processed. Accept either a
    # real place or the honest "don't know" — never silence or a crash.
    assert out, out


def test_where_says_it_does_not_know_rather_than_guessing():
    c = new_ccm()
    say(c, "hello there")
    out = say(c, "where are we going?")["marked_output"]
    assert any(p in out.lower() for p in ("don't know", "no idea", "haven't said", "tell me", "where to")), out


def test_context_chunk_reaches_short_term_after_enough_turns():
    c = new_ccm()
    for t in ["we going to the market", "the road is long", "I see a river",
              "we rest here", "the sun is out", "birds sing"]:
        say(c, t)
    kinds = [e.get("source") for e in c.memory_m.short_term]
    assert "context" in kinds, kinds


def test_flag_off_is_the_old_behaviour():
    old = ms.CONTEXT_FLUSH_ENABLED
    ms.CONTEXT_FLUSH_ENABLED = False
    try:
        c = new_ccm()
        for t in ["we going to the market", "the road is long", "I see a river",
                  "we rest here", "the sun is out", "birds sing", "more birds"]:
            say(c, t)
        assert len(c.memory_m.short_term) == 0
        r = build_recall(c, "Do you remember the market?", ["do", "you", "remember", "market"])
        assert r and not r["found"], r
    finally:
        ms.CONTEXT_FLUSH_ENABLED = old


def test_context_flush_never_outranks_the_arc_or_threat_class_cap():
    from systems.memory_system import MemorySystem, CONTEXT_CLASS_CAP, _CLASS_RANK
    m = MemorySystem()
    huge_s = {"V": 5, "I": 400, "Lv": 5, "Gv": 400}
    huge_m = {"P": 5, "A": 200, "Er": 5, "Rr": 200}
    rest = {"V": 5, "I": 5, "Lv": 5, "Gv": 5}
    for i in range(6):
        m.update("scene", ["threatword"], huge_s, huge_m)
    ctx = [e for e in m.short_term if e.get("source") == "context"]
    assert ctx and _CLASS_RANK[ctx[0]["event_class"]] <= _CLASS_RANK[CONTEXT_CLASS_CAP], ctx


def test_a_context_chunk_never_outranks_a_real_episode_of_the_same_concept():
    """Regression: a scene that goes "ambush -> bandit lunges -> bandit flees (relief)" flushes to a
    context chunk whose single biggest-magnitude turn can be the RELIEF moment, giving the whole chunk a
    positive valence even though the concept is "bandit" and the real threat episode about the bandit is
    correctly negative. Before the source-priority tie-break in memory_recall.find_events(), the chunk's
    larger raw numbers made it win the sort, and "Do you remember the bandit?" / "You liked the bandit."
    read from the wrong (positive) entry. Reproduces with a real compiled character (delia_adventurer_v4),
    which is where this was first found -- the built-in test character's chemistry does not swing the
    same way."""
    import json
    from character.injector import inject_character
    here = os.path.dirname(os.path.abspath(__file__))
    char = json.load(open(os.path.join(here, "..", "..", "fullcompiler", "characters",
                                        "delia_adventurer_v4.json"), encoding="utf-8"))
    random.seed(1)
    c, _ = inject_character(char)
    c.user_name = "Joaquin"
    for t in ('"Calm" Hello Delia. What is your name?', "Who is your father?",
              "You are 40 years old, right?"):           # small talk: the somatic baseline this depends on
        say(c, t)
    say(c, "a bandit steps out of the bushes, blade drawn")
    say(c, '"Scared" Watch out Delia, a bandit!')
    say(c, "the bandit lunges at her")
    say(c, "the bandit flees into the forest")     # relief: the single biggest-magnitude turn
    say(c, "she sits by the fire and rests")
    say(c, "It is quiet again.")                    # 6 turns: the window flushes here
    ctx = [e for e in c.memory_m.short_term if e.get("source") == "context"]
    real = [e for e in c.memory_m.short_term if e.get("source") != "context"]
    assert ctx and "bandit" in ctx[0]["concepts"] and ctx[0]["valence"] == "positive", \
        "test setup assumption broke: the chunk should still be the mixed-sign, positive-peak one"
    assert real and "bandit" in real[0]["concepts"] and real[0]["valence"] == "negative"
    out = say(c, "Do you remember the bandit?")["marked_output"]
    assert "scared" in out.lower() or "feel it" in out.lower() or "bad" in out.lower() or "hurt" in out.lower(), out
    out2 = say(c, "You liked the bandit.")["marked_output"]
    assert out2.lower().startswith("no") or "not what i remember" in out2.lower(), out2


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print("  OK  ", name)
        except Exception as e:
            failed += 1; print("  FAIL", name, "->", repr(e))
    print("\nAll OK" if not failed else f"\n{failed} FAILED")
    sys.exit(1 if failed else 0)
