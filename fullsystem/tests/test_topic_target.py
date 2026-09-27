# tests/test_topic_target.py — who/what the reply is about (core/topic_target.py).
# Usage (from the project root):  python tests/test_topic_target.py
import os, sys, json, random, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "displayer"))

from core import topic_target as tt
from core.response_matrix import select_axis_response, RESPONSE_MATRIX

TOPIC_CASES = {                       # input -> expected target when a speaker is set
    "The bandit is dangerous.": "the bandit",
    "What is that noise?": "the noise",
    "There is a monster outside.": "the monster",
    "The door was broken by the bandit.": "the bandit",       # passive: the agent, not "the door"
    "If the bandit moves, we are dead.": "the bandit",
    "A bandit draws a knife.": "the bandit",
    "Look at the bandit!": "the bandit",
}
SPEAKER_CASES = [                     # no clear topic -> the speaker, as before
    "Do you know him?", "Why did you run away?", "Run!", "Hello there.", "I love you.",
    "He is coming.", "You are brave and fast.", "There is no way around it.",
]


def _r(text, focus, seed=2, axis="V/P", cat="danger"):
    return select_axis_response(axis, cat, "Delia", raw_text=text, forced_focus=focus, rng=random.Random(seed))


def test_topic_wins_over_the_speaker_for_user_and_named_speakers():
    for focus in ("user", "Joaquin", "the bandit"):
        for text, expected in TOPIC_CASES.items():
            r = _r(text, focus)
            assert (r["subject"], r["target_source"]) == (expected, "topic"), (focus, text, r["subject"])


def test_no_clear_topic_falls_back_to_the_speaker():
    for focus in ("user", "Joaquin"):
        for text in SPEAKER_CASES:
            r = _r(text, focus)
            assert (r["subject"], r["target_source"]) == (focus, "speaker"), (focus, text, r["subject"])


def test_narrator_turns_keep_text_subject_and_get_the_fixes():
    assert _r("The bandit is dangerous.", None)["subject"] == "the bandit"
    assert _r("The door was broken by the bandit.", None)["subject"] == "the bandit"
    r = _r("There is no way around it.", None)
    assert (r["subject"], r["target_source"]) == ("that", "default")
    r = _r("Hello there.", None)
    assert (r["subject"], r["target_source"]) == ("that", "default")


def test_reacting_character_is_never_the_topic():
    assert not tt._is_valid_topic("Delia", "Delia")
    assert not tt._is_valid_topic("the way")
    assert not tt._is_valid_topic("him") and not tt._is_valid_topic("something")
    assert tt._is_valid_topic("the bandit", "Delia") and tt._is_valid_topic("Joaquin", "Delia")


def test_flag_off_pins_the_speaker_again():
    tt.USE_TOPIC_TARGET = False
    try:
        for text in list(TOPIC_CASES) + SPEAKER_CASES:
            r = _r(text, "user")
            assert (r["subject"], r["target_source"]) == ("user", "speaker"), text
    finally:
        tt.USE_TOPIC_TARGET = True


def test_questions_no_longer_all_target_you():
    # the measurement that started this: 137/144 question replies said "you"
    cells = [(c, a) for c, row in RESPONSE_MATRIX.items() for a in row]
    about_you = total = 0
    for i, text in enumerate(("What is that noise?", "Why did you run away?", "Do you know him?")):
        for c, a in cells:
            r = _r(text, "user", seed=i, axis=a, cat=c)
            total += 1
            about_you += r["subject"] == "user"
    assert 0 < about_you < total   # noise-question moved to the topic; "him"/"why you" stay with the speaker
    noise = [_r("What is that noise?", "user", seed=s, axis=a, cat=c)["subject"] for c, a in cells for s in range(2)]
    assert set(noise) == {"the noise"}


def test_dialogue_and_action_line_name_the_same_target_end_to_end():
    import app
    from core.marker_parser import parse_marked_input as P
    delia = os.path.join(HERE, "..", "..", "fullcompiler", "characters", "delia_adventurer_v4.json")
    random.seed(3)
    ccm, _ = app.inject_character(json.load(open(delia)))
    out = ccm.process(text="", marked_input=P("The bandit is dangerous. <<a bandit draws a knife>>"),
                      speaker="user")["marked_output"]
    action = out[out.index("<<"):]
    assert "bandit" in action and "you" not in action.lower(), out
    random.seed(3)
    ccm, _ = app.inject_character(json.load(open(delia)))
    out2 = ccm.process(text="", marked_input=P('"Friendly" Hello there. <<smiles>>'), speaker="user")["marked_output"]
    assert "you" in out2.lower() and "bandit" not in out2.lower(), out2


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("ok  ", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e)[:300])
    print("\n%s" % ("ALL OK" if not fails else f"{fails} FAILED"))
    sys.exit(1 if fails else 0)
