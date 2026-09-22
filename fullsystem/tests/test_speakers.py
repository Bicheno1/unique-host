# tests/test_speakers.py — narrator / user / named speakers (engine selector + displayer wiring)
# Run: python tests/test_speakers.py
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


def test_dropdown_labels_map_to_engine_speakers():
    assert app.engine_speaker("Narrator") == "narrator" and app.engine_speaker("") == "narrator"
    assert app.engine_speaker(None) == "narrator"
    assert app.engine_speaker("You") == "user" and app.engine_speaker("you (user)") == "user"
    assert app.engine_speaker("Joaquin") == "Joaquin" and app.engine_speaker("bandit") == "bandit"


def test_inline_prefix_switches_only_known_names_or_at_new():
    known = ["Joaquin", "bandit"]
    assert app.split_speaker_prefix("Joaquin: Watch out!", known) == ("Joaquin", "Watch out!")
    assert app.split_speaker_prefix("joaquin: Watch out!", known) == ("Joaquin", "Watch out!")
    assert app.split_speaker_prefix("Narrator: A bandit appears.", known) == ("Narrator", "A bandit appears.")
    assert app.split_speaker_prefix("You: Hello", known) == ("You", "Hello")
    assert app.split_speaker_prefix("@Marta: Hello there", known) == ("Marta", "Hello there")
    assert app.split_speaker_prefix("Warning: the bridge is out", known) == (None, "Warning: the bridge is out")
    assert app.split_speaker_prefix("Marta: hi", known) == (None, "Marta: hi")           # unknown name: no switch
    assert app.split_speaker_prefix('"Angry" Get out! <<slams the door>>', known)[0] is None


def test_the_engine_reacts_to_who_is_speaking():
    text = '"Friendly" Hello there. <<smiles>>'
    out = {}
    for sp in ("narrator", "user", "Joaquin", "bandit"):
        out[sp] = load().process(text="", marked_input=P(text), speaker=sp)["marked_output"]
    assert "Joaquin" in out["Joaquin"] and "the bandit" in out["bandit"] and "you" in out["user"].lower()
    assert "Joaquin" not in out["narrator"] and "bandit" not in out["narrator"]


def test_memory_is_tagged_with_the_current_speaker():
    ccm = load()
    for t in ['<<locks her in a cage>>', '<<the cage door slams shut>>', '<<she is trapped in the cage>>',
              '<<a warm breeze>>', '<<birds sing>>', 'Everything is quiet.']:
        ccm.process(text="", marked_input=P(t), speaker="Mark")
    m = ccm.memory_m
    events = m.short_term + m.medium_term + m.long_term
    assert any("mark" in e["concepts"] for e in events if e.get("source") == "threat"), [e["concepts"] for e in events]
    # "What do you think about me?" is about whoever asks
    mark = ccm.process(text="", marked_input=P("What do you think about me?"), speaker="Mark")
    assert mark["recall"]["found"] and mark["recall"]["subject"] == "mark"
    marta = ccm.process(text="", marked_input=P("What do you think about me?"), speaker="Marta")
    assert not marta["recall"]["found"]                                        # a stranger who was never there
    joaquin = ccm.process(text="", marked_input=P("What do you think about me?"), speaker="Joaquin")
    assert joaquin["recall"]["found"] and joaquin["recall"].get("bond")        # her seeded friend


def test_narrator_and_user_use_the_players_name():
    ccm = load()
    ccm.user_name = "Joaquin"
    for sp in ("narrator", "user"):
        s = ccm.process(text="", marked_input=P("What do you think about me?"), speaker=sp)
        assert s["recall"]["subject"] == "joaquin" and s["recall"].get("bond"), (sp, s["recall"])


def test_the_action_line_names_the_player_not_the_word_user():
    for name, expected in (("Marta", "Marta"), (None, "you")):
        ccm = load()
        ccm.user_name = name
        out = ccm.process(text="", marked_input=P('"Friendly" Hello there. <<smiles>>'), speaker="user")["marked_output"]
        action = out[out.index("<<"):]
        assert "user" not in action and expected in action, (name, out)


def test_chat_bubbles_name_who_is_talking():
    ccm = load()
    h, ccm, *_ = app.chat_step_fields(ccm, "Calm", "Hello there.", "", [], "Marta", "You", [])
    assert h[0]["content"].startswith("**Marta**") and h[1]["content"].startswith("**Delia**")
    h, ccm, *_ = app.chat_step_fields(ccm, "", "", "a wind rises", h, "Marta", "Narrator", [])
    assert h[2]["content"].startswith("**Narrator**")
    h, ccm, *_ = app.chat_step_fields(ccm, "", "hi", "", h, "", "You", [])
    assert h[4]["content"].startswith("**You**")


def test_chat_step_ui_grows_the_list_and_keeps_the_speaker():
    ccm = load()
    h, ccm, cleared, dd, speakers = app.chat_step_ui(ccm, "@Mark: Hello there.", [], "Joaquin", "Narrator", [])
    assert speakers == ["Mark"] and dd["value"] == "Mark" and dd["choices"] == ["Narrator", "You", "Mark"]
    assert h[0]["content"].startswith("**Mark**") and "Hello there" in h[0]["content"] and cleared == ""
    h, ccm, _, dd, speakers = app.chat_step_ui(ccm, "Narrator: a wind rises", h, "Joaquin", "Mark", speakers)
    assert dd["value"] == "Narrator" and speakers == ["Mark"] and h[2]["content"] == "**Narrator**: a wind rises"
    h, ccm, _, dd, speakers = app.chat_step_ui(ccm, "I am here", h, "Joaquin", "You", speakers)
    assert h[4]["content"].startswith("**Joaquin**")
    h, ccm, _, dd, speakers = app.chat_step_ui(ccm, "bandit smiles", h, "Joaquin", "bandit", speakers)   # typed custom value
    assert "bandit" in speakers and h[6]["content"].startswith("**bandit**")


def test_no_character_and_empty_message_do_not_crash():
    h, c, _, dd, sp = app.chat_step_ui(None, "hello", [], "", "Narrator", [])
    assert "No character loaded" in h[-1]["content"]
    h2, _, _, _, _ = app.chat_step_ui(None, "   ", [], "", "Narrator", [])
    assert h2 == []


def test_the_ui_still_builds_with_the_selector():
    demo = app.build_demo()
    assert demo is not None


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
