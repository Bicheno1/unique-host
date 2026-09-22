# tests/test_memory_recall.py — memory recall on request (core/memory_recall.py)
#
# Events are created through the REAL MemorySystem.update() closing code (a peak, then a
# return to rest) so valence / closed_at / tiers are what play would produce.
# Run: python tests/test_memory_recall.py
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motors.cycle_manager_v5 import CycleManagerV5
from core.memory_recall import detect_recall_query, build_recall
from core.marker_parser import parse_marked_input
import core.memory_recall as mr

BAD_S  = {"V": 10, "I": 150, "Lv": 30, "Gv": 10}     # somatic peak, V<I  = bad
BAD_M  = {"P": 5,  "A": 80,  "Er": 40, "Rr": 10}     # mental  peak, A>P  = bad
GOOD_S = {"V": 150, "I": 10, "Lv": 30, "Gv": 10}
GOOD_M = {"P": 80, "A": 5,  "Er": 40, "Rr": 10}
REST_S = {"V": 5, "I": 5, "Lv": 5, "Gv": 5}
REST_M = {"P": 5, "A": 5, "Er": 5, "Rr": 5}


def new_ccm(user="Joaquin"):
    random.seed(1)
    ccm = CycleManagerV5()
    ccm.character_name = "Delia"
    ccm.user_name = user
    return ccm


def live_event(ccm, concepts, good=False, scale=1.0):
    """Peak then rest through MemorySystem.update() -> one closed event in short-term."""
    ign = {ccm.user_name.lower()} if ccm.user_name else set()   # what cycle_manager does
    ccm.memory_s.ignore_concepts = ccm.memory_m.ignore_concepts = ign
    s = {k: v * scale for k, v in (GOOD_S if good else BAD_S).items()}
    m = {k: v * scale for k, v in (GOOD_M if good else BAD_M).items()}
    for mem in (ccm.memory_s, ccm.memory_m):
        mem.update("scene", concepts, REST_S, REST_M)   # not started
        mem.update("scene", concepts, s, m)              # start + peak
        mem.update("scene", concepts, s, m)
        mem.update("scene", concepts, REST_S, REST_M)    # back to rest -> closes
        mem.update("scene", concepts, REST_S, REST_M)


def ask(ccm, text):
    return build_recall(ccm, text, [])


def concepts_of(text):
    # what the engine's tokenizer would hand over: the lexicon-resolved words
    from db.db_concepts import resolve_concept
    out = []
    for t in text.lower().replace("?", "").replace("!", "").split():
        c = resolve_concept(t)
        if c and c not in out:
            out.append(c)
    return out


def ask_full(ccm, text):
    return build_recall(ccm, text, concepts_of(text))


def test_detection():
    yes = {"Do you remember the monster?": ("remember", None),
           "Do you remember yesterday?": ("remember", "past"),
           "Do you remember earlier?": ("remember", "recent"),
           "Do you remember the bandit from a long time ago?": ("remember", "distant"),
           "What happened yesterday?": ("remember", "past"),
           "What do you think about me?": ("about_me", None),
           "What do you think of me, Delia?": ("about_me", None),
           "Do you trust me?": ("about_me", None),
           "Do you remember me?": ("about_me", None)}
    for text, (kind, time) in yes.items():
        q = detect_recall_query(text)
        assert q and q["kind"] == kind and q["time"] == time, (text, q)
    for text in ["Who are you?", "Remember to run!", "Watch out, a monster!", "What is your name?", ""]:
        assert detect_recall_query(text) is None, text


def test_subject_recall_uses_stored_event():
    ccm = new_ccm()
    live_event(ccm, ["monster", "forest"])
    assert ccm.memory_m.short_term, "the event should have closed"
    r = ask_full(ccm, "Do you remember the monster?")
    assert r["found"] and r["subject"] == "monster" and "monster" in r["phrase"], r
    assert r["action"] == "remembering the monster"


def test_feeling_follows_stored_valence():
    bad, good = new_ccm(), new_ccm()
    live_event(bad, ["monster"], good=False)
    live_event(good, ["monster"], good=True)
    assert bad.memory_m.short_term[0]["valence"] == "negative"
    assert good.memory_m.short_term[0]["valence"] == "positive"
    neg = {f for k in ((("negative", False)), (("negative", True))) for f in mr._FEELING[k]}
    pos = {f for k in ((("positive", False)), (("positive", True))) for f in mr._FEELING[k]}
    bad_phrase = ask_full(bad, "Do you remember the monster?")["phrase"]
    good_phrase = ask_full(good, "Do you remember the monster?")["phrase"]
    assert any(f in bad_phrase for f in neg), bad_phrase
    assert any(f in good_phrase for f in pos), good_phrase


def test_unknown_subject_is_not_invented():
    ccm = new_ccm()
    live_event(ccm, ["monster"])
    r = ask_full(ccm, "Do you remember the dragon?")
    assert not r["found"] and "dragon" in r["phrase"]


def test_time_buckets_and_honest_when():
    ccm = new_ccm()
    live_event(ccm, ["monster"])                        # sits in short-term
    r = ask_full(ccm, "Do you remember yesterday?")     # asks for medium, only short exists
    assert r["found"] and r["tier"] == "short" and "just now" in r["phrase"], r   # says when it REALLY was
    ccm.memory_m.medium_term.append(dict(ccm.memory_m.short_term[0], concepts=["bandit"]))
    r = ask_full(ccm, "Do you remember yesterday?")
    assert r["tier"] == "medium" and "a while back" in r["phrase"], r
    ccm.memory_m.long_term.append(dict(ccm.memory_m.short_term[0], concepts=["cave"], is_nuclear=True))
    r = ask_full(ccm, "Do you remember, long ago?")
    assert r["tier"] == "long" and "a long time ago" in r["phrase"], r
    assert not ask_full(new_ccm(), "Do you remember yesterday?")["found"]


def test_about_me():
    none = new_ccm()
    assert not ask(none, "What do you think about me?")["found"]

    pos = new_ccm(); live_event(pos, ["joaquin", "camp"], good=True)
    r = ask(pos, "What do you think about me?")
    assert r["found"] and r["positive"] == 1 and r["events"] == 1
    assert r["phrase"] in mr._ABOUT_ME_POS + mr._ABOUT_ME_POS_STRONG

    neg = new_ccm(); live_event(neg, ["joaquin", "monster"], good=False)
    assert ask(neg, "What do you think about me?")["phrase"] in mr._ABOUT_ME_NEG + mr._ABOUT_ME_NEG_STRONG

    mixed = new_ccm(); live_event(mixed, ["joaquin", "camp"], good=True); live_event(mixed, ["joaquin", "cave"], good=False)
    assert ask(mixed, "What do you think about me?")["phrase"] in mr._ABOUT_ME_MIXED

    other = new_ccm(user="Marta"); live_event(other, ["joaquin"], good=True)   # someone else's memories
    assert not ask(other, "What do you think about me?")["found"]


def test_about_me_for_a_bonded_friend():
    from core.memory_recall import _ABOUT_ME_BOND, _ABOUT_ME_BOND_MIXED
    c = new_ccm()
    c.identity_anchor_system.set_anchors([{"concept": "joaquin", "target_stat": "company"}])
    r = ask(c, "What do you think about me?")
    assert r["found"] and r["bond"] and r["phrase"] in _ABOUT_ME_BOND, r          # no events: the bond speaks
    live_event(c, ["joaquin", "monster"], good=False)
    r = ask(c, "What do you think about me?")
    assert r["bond"] and r["phrase"] in _ABOUT_ME_BOND_MIXED, r                    # scary scenes do not turn a friend into a threat
    other = new_ccm(user="Marta")
    other.identity_anchor_system.set_anchors([{"concept": "joaquin", "target_stat": "company"}])
    assert not ask(other, "What do you think about me?")["found"]                 # a stranger is still a stranger


def test_user_name_tags_every_event():
    ccm = new_ccm()
    seen = []
    orig = ccm.memory_m.update
    ccm.memory_m.update = lambda text, concepts, s, m, *a: (seen.append(list(concepts)), orig(text, concepts, s, m, *a))[1]
    ccm.process(text="", marked_input=parse_marked_input("<<a monster roars>>"))
    assert seen and seen[0][0] == "joaquin", seen


def test_seeded_fear_and_comfort_can_be_recalled():
    import json
    from character.injector import inject_character
    ch = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "fullcompiler",
                                     "characters", "delia_adventurer_v4.json")))
    ch["core_identity_rules"]["custom_fear"]["concepts"] = ["cage"]
    ch["core_identity_rules"]["custom_comfort"]["concepts"] = ["road"]
    ccm, _ = inject_character(ch)
    ccm.user_name = "Joaquin"
    fear = ask_full(ccm, "Do you remember the cage?")
    assert fear["found"] and "a long time ago" in fear["phrase"]
    assert any(f in fear["phrase"] for k in (("negative", True), ("negative", False)) for f in mr._FEELING[k])
    comfort = ask_full(ccm, "Do you remember the road?")
    assert any(f in comfort["phrase"] for k in (("positive", True), ("positive", False)) for f in mr._FEELING[k])


def test_variants_do_not_repeat_back_to_back():
    ccm = new_ccm()
    live_event(ccm, ["monster"])
    a = ask_full(ccm, "Do you remember the monster?")["phrase"]
    b = ask_full(ccm, "Do you remember the monster?")["phrase"]
    assert a != b


def test_engine_end_to_end_and_other_questions_untouched():
    ccm = new_ccm()
    live_event(ccm, ["monster"])
    s = ccm.process(text="", marked_input=parse_marked_input("Do you remember the monster?"))
    assert s["recall"] and s["recall"]["found"]
    assert "monster" in s["marked_output"] and "<<remembering the monster>>" in s["marked_output"], s["marked_output"]
    s2 = ccm.process(text="", marked_input=parse_marked_input("Who are you?"))
    assert s2["recall"] is None and "<<remembering" not in s2["marked_output"]


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
