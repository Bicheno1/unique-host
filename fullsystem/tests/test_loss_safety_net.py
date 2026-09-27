# tests/test_loss_safety_net.py — core/loss_safety_net.py: the minimal wording guard for a known wording hole
# (NOT option A/B/C -- see that module's docstring for exactly what this does and does not fix).
# Run: python tests/test_loss_safety_net.py
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = os.path.join(HERE, "..", "..", "fullcompiler", "characters")

import core.loss_safety_net as lsn
from core.marker_parser import parse_marked_input as P


def _load(fname):
    return json.load(open(os.path.join(CHARS, fname), encoding="utf-8"))


def _play(fname, turns, seed=3):
    from character.injector import inject_character
    random.seed(seed)
    ccm, _ = inject_character(_load(fname))
    ccm.user_name = "Joaquin"
    return [ccm.process(text="", marked_input=P(t))["marked_output"] for t in turns]


# ── unit-level: is_loss_scene() / applies() ──────────────────────────────────

def test_feeling_word_subject_is_detected_with_or_without_an_article():
    for subj in ("grief", "the grief", "orphan", "the orphan", "widow"):
        assert lsn.is_loss_scene("", subj), subj


def test_loss_verb_in_raw_text_is_detected_regardless_of_subject():
    assert lsn.is_loss_scene("her home is destroyed", "the home")
    assert lsn.is_loss_scene("someone steals her purse", "the purse")
    assert lsn.is_loss_scene("the village was burned", "the village")


def test_negation_cancels_the_loss_verb():
    assert not lsn.is_loss_scene("nobody stole anything", "that")
    assert not lsn.is_loss_scene("it was not destroyed", "that")


def test_ordinary_scenes_are_not_flagged():
    for text, subj in [("a bandit lunges at her", "the bandit"), ("she sits by the fire", "the fire"),
                        ("a warm breeze", "the breeze"), ("we win the game", "the game")]:
        assert not lsn.is_loss_scene(text, subj), (text, subj)


def test_applies_only_fires_for_the_two_literal_modes():
    assert lsn.applies("attack", "", "grief")
    assert lsn.applies("accept", "", "grief")
    for mode in ("investigate", "suppress", "signal", "observe", "cooperate", "group", "formulate"):
        assert not lsn.applies(mode, "", "grief"), mode


def test_flag_off_is_the_old_behaviour():
    old = lsn.LOSS_SAFETY_NET_ENABLED
    lsn.LOSS_SAFETY_NET_ENABLED = False
    try:
        assert not lsn.applies("attack", "her home is destroyed", "the home")
    finally:
        lsn.LOSS_SAFETY_NET_ENABLED = old


def test_no_double_article_in_the_fallback():
    assert "the the" not in lsn.fallback_sentence("the home").lower()
    assert "the the" not in lsn.fallback_sentence("home").lower()
    assert lsn.fallback_sentence("you").lower().startswith(("i ", "there's"))  # "you" is not re-articled


# ── end to end: the exact scenes originally used to spec this guard ───────

def test_the_four_headline_examples_no_longer_produce_nonsense_wording():
    """The draft's own flagged examples. This does not assert the MODE changes (still the character's
    dominant axis, per LOSS_REACTION_DRAFT.md section 3 -- that is option A/B/C, not this patch) --
    only that the sentence stops being a literal category error when that mode is attack/accept."""
    scenes = ["<<grief fills her>>", "<<an orphan cries>>",
              "<<her home is destroyed>>", "<<someone steals her purse>>"]
    banned = ("attack the grief", "attacking the grief", "attack the orphan", "attacking the orphan",
              "tear into the orphan", "tearing into the orphan",
              "thank", "welcom", "accept the purse", "accepting the purse",
              "accept the home", "accepting the home")
    for f in ("delia_adventurer_v4.json", "joaquin_adventurer_v2.json"):
        for seed in (3, 7, 11):
            out = _play(f, scenes, seed=seed)
            for text, line in zip(scenes, out):
                low = line.lower()
                assert not any(b in low for b in banned), (f, seed, text, line)


def test_negated_loss_verb_still_lets_the_mode_speak_normally():
    """"nobody stole anything" must NOT be treated as a loss scene -- the safety net only guards real
    loss/destruction/theft, not the mention of the words."""
    out = _play("delia_adventurer_v4.json", ["nobody stole anything"], seed=3)[0].lower()
    assert "i don't know what to do" not in out and "nothing i can do" not in out, out


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
