# tests/test_message_fields.py — Emotion / Text / Action as three separate boxes (displayer/app.py)
# Run: python tests/test_message_fields.py
import os, sys, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "displayer"))
import app
from core.marker_parser import parse_marked_input as P

DELIA = os.path.join(HERE, "..", "..", "fullcompiler", "characters", "delia_adventurer_v4.json")


def load():
    random.seed(3)
    ccm, _ = app.inject_character(json.load(open(DELIA)))
    return ccm


def test_boxes_become_the_engine_dict():
    assert app.compose_marked("Angry", "Get out", "slams the door") == {"emotion": "Angry", "dialogue": "Get out", "action": "slams the door"}
    assert app.compose_marked("", "Hello", "") == {"emotion": None, "dialogue": "Hello", "action": None}
    assert app.compose_marked("  ", " ", "waves") == {"emotion": None, "dialogue": None, "action": "waves"}
    assert app.compose_marked("", "", "") == {"emotion": None, "dialogue": None, "action": None}


def test_old_one_line_syntax_still_works_in_the_text_box():
    assert app.compose_marked("", '"Angry" Get out <<slams the door>>', "") == P('"Angry" Get out <<slams the door>>')
    # but if the other boxes are used, the text is taken literally
    assert app.compose_marked("Angry", 'He said "no" to me', "") == {"emotion": "Angry", "dialogue": 'He said "no" to me', "action": None}


def test_boxes_and_syntax_give_the_same_engine_result():
    a = load().process(text="", marked_input=app.compose_marked("Angry", "Get away from her!", "raises a blade"))
    b = load().process(text="", marked_input=P('"Angry" Get away from her! <<raises a blade>>'))
    assert a["marked_output"] == b["marked_output"] and a["concepts"] == b["concepts"]


def test_fields_handler_sends_the_three_fragments_and_clears_the_boxes():
    ccm = load()
    seen = []
    orig = ccm.process
    ccm.process = lambda text="", marked_input=None, speaker="narrator": (seen.append((marked_input, speaker)), orig(text=text, marked_input=marked_input, speaker=speaker))[1]
    out = app.chat_step_fields(ccm, "Scared", "Watch out!", "draws a blade", [], "Joaquin", "Joaquin", [])
    history, _, e, t, a, dd, speakers = out
    assert seen == [({"emotion": "Scared", "dialogue": "Watch out!", "action": "draws a blade"}, "Joaquin")]
    assert (e, t, a) == ("", "", "") and speakers == ["Joaquin"] and dd["value"] == "Joaquin"
    assert history[0]["content"] == "**Joaquin** _(Scared)_: Watch out! *draws a blade*"
    assert history[1]["content"].startswith("**Delia**") and "*" in history[1]["content"]


def test_each_box_is_optional_but_one_is_needed():
    ccm = load()
    for args in (("", "Hello there.", ""), ("Calm", "", ""), ("", "", "sits down")):
        h, _, e, t, a, _, _ = app.chat_step_fields(ccm, *args, [], "", "Narrator", [])
        assert len(h) == 2, args
    typed = ("", "   ", "  ")
    h, _, e, t, a, _, _ = app.chat_step_fields(ccm, *typed, [], "", "Narrator", [])
    assert h == [] and (e, t, a) == typed                                   # nothing sent, nothing cleared


def test_inline_speaker_switch_works_from_the_text_box():
    ccm = load()
    h, _, e, t, a, dd, speakers = app.chat_step_fields(ccm, "Friendly", "@Mark: Hello there.", "smiles", [], "", "Narrator", [])
    assert speakers == ["Mark"] and dd["value"] == "Mark"
    assert h[0]["content"] == "**Mark** _(Friendly)_: Hello there. *smiles*"


def test_bubbles_render_missing_parts_cleanly():
    assert app.format_turn("Mark", {"emotion": None, "dialogue": "Hi", "action": None}) == "**Mark**: Hi"
    assert app.format_turn("Mark", {"emotion": "Calm", "dialogue": None, "action": "sits"}) == "**Mark** _(Calm)_: *sits*"
    assert app.format_turn("Mark", {"emotion": None, "dialogue": None, "action": None}) == ""


def test_no_character_loaded_and_the_ui_builds():
    h, _, *_ = app.chat_step_fields(None, "", "hello", "", [], "", "Narrator", [])
    assert "No character loaded" in h[-1]["content"]
    assert app.build_demo() is not None


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
