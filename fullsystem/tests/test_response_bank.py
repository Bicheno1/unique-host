# tests/test_response_bank.py — per-mode phrase bank (core/response_bank.py).
# Usage (from the project root):  python tests/test_response_bank.py
import os, sys, re, random, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core import response_bank as rb
from core.response_matrix import RESPONSE_MATRIX, SOCIAL_POSITIONING, AXIS_TO_CATEGORY

PRONOUNS = ["I", "We", "You", "They"]
SUBJECTS = ["the bandit", "Mark", "that", "the bread"]
LEANS = {"V/P", "I/A", "Lv/Er", "Gv/Rr"}


def _all_keys():
    keys = set()
    for cat, row in RESPONSE_MATRIX.items():
        for axis, verb in row.items():
            keys.add(rb.bank_key(verb, axis))
    return keys


def test_every_matrix_cell_has_a_bank():
    missing = _all_keys() - set(rb.BANK)
    assert not missing, missing
    extra = set(rb.BANK) - _all_keys()
    assert not extra, extra


def test_bank_size_and_lean_variety():
    for key, variants in rb.BANK.items():
        assert len(variants) >= 5, (key, len(variants))
        leans = {l for l, _ in variants}
        assert leans <= LEANS, (key, leans)
        assert len(leans) >= 3, (key, leans)       # the profile needs options
        texts = [t for _, t in variants]
        assert len(set(texts)) == len(texts), key  # no duplicates


def test_every_template_formats_for_every_pronoun_and_subject():
    for key, variants in rb.BANK.items():
        for _, t in variants:
            for p in PRONOUNS:
                for s in SUBJECTS:
                    out = t.format(subject=s, subject_cap=s[:1].upper() + s[1:],
                                   mode="observe", pronoun=p,
                                   pronoun_lower=("I" if p == "I" else p.lower()))
                    assert "{" not in out and "}" not in out, (key, t)
                    assert out.strip(), (key, t)


def test_pronoun_agreement_is_safe_for_all_four_pronouns():
    # Only base-form verbs after the pronoun: no am/are/is/was,
    # 'm/'re/'s, possessives or reflexives (I/We/You/They change those forms).
    bad_after_pronoun = re.compile(
        r"\{pronoun(?:_lower)?\}(?:'m|'re|'s|\s+(?:am|are|is|was|were|has)\b)")
    bad_words = re.compile(r"\b(my|your|our|their|myself|yourself|ourselves|themselves)\b", re.I)
    for key, variants in rb.BANK.items():
        for _, t in variants:
            assert not bad_after_pronoun.search(t), (key, t)
            assert not bad_words.search(t), (key, t)


def test_no_third_person_verb_right_after_subject():
    # {subject} can be "you" (speaker "user"): "You is/passes/wins" would break.
    third = re.compile(r"\{subject(?:_cap)?\}\s+(?:is|has|does|goes)\b")
    for key, variants in rb.BANK.items():
        for _, t in variants:
            assert not third.search(t), (key, t)
            for p in PRONOUNS:
                out = t.format(subject="you", subject_cap="You", mode="observe",
                               pronoun=p, pronoun_lower=("I" if p == "I" else p.lower()))
                assert not re.search(r"\b[Yy]ou (is|has|does|goes|wins|passes|fits|feels|means)\b", out), (key, out)


def test_user_speaker_reads_as_you():
    out = rb.render_from_bank("formulate", "formulate", "user", "I", axis="Lv/Er", rng=random.Random(1))
    assert "user" not in out.lower().split() and "you" in out.lower(), out


def test_fill_pronoun_matches_mode_axis():
    # Each mode comes out with the pronoun of its cell's axis (design decision).
    for cat, row in RESPONSE_MATRIX.items():
        for axis, verb in row.items():
            key = rb.bank_key(verb, axis)
            pron = SOCIAL_POSITIONING[axis]["pronoun"]
            rng = random.Random(1)
            out = rb.render_from_bank(verb, verb, "the bandit", pron, axis=axis, rng=rng)
            assert out and out[0].isupper(), (key, out)


def test_never_repeats_last_variant():
    rng = random.Random(7)
    for key in rb.BANK:
        mem = {}
        last = None
        for _ in range(300):
            idx = rb.pick_variant(key, None, None, mem, rng)
            assert idx != last, (key, idx)
            last = idx


def test_flat_profile_is_roughly_uniform():
    rng = random.Random(3)
    key = "observe"
    n = len(rb.BANK[key])
    counts = [0] * n
    for _ in range(6000):
        counts[rb.pick_variant(key, None, None, None, rng)] += 1
    assert min(counts) > 6000 / n * 0.75 and max(counts) < 6000 / n * 1.25, counts


def _gains(axis_short, high=9.0, low=2.0):
    return {c: {a: (high if a == axis_short else low) for a in ["V", "I", "Gv", "Lv"]}
            for c in ["danger", "benefit", "neutral", "unclassifiable"]}


def _share(key, lean, gains, n=4000):
    rng = random.Random(11)
    hits = 0
    for _ in range(n):
        idx = rb.pick_variant(key, gains, None, None, rng)
        hits += rb.BANK[key][idx][0] == lean
    return hits / n


def test_profile_shifts_choice_toward_matching_lean():
    for key in ("observe", "protect", "attack", "formulate"):
        composed   = _share(key, "Gv/Rr", _gains("Gv"))
        impulsive  = _share(key, "Gv/Rr", _gains("Lv"))
        assert composed > impulsive + 0.10, (key, composed, impulsive)
        emo_imp = _share(key, "Lv/Er", _gains("Lv"))
        emo_com = _share(key, "Lv/Er", _gains("Gv"))
        assert emo_imp > emo_com + 0.10, (key, emo_imp, emo_com)


def test_extreme_profile_never_zeroes_any_variant():
    # An extreme profile biases but does not eliminate: variety remains.
    for key in rb.BANK:
        w = rb.variant_weights(key, _gains("Gv", 10.0, 0.0), None)
        assert min(w) >= rb.MIN_WEIGHT and all(x > 0 for x in w), (key, w)


def test_state_fit_accepts_somatic_and_mental_state():
    som = {"V": 10, "I": 10, "Lv": 60, "Gv": 20}
    men = {"P": 10, "A": 10, "Er": 60, "Rr": 20}
    assert abs(rb.state_fit(som, "Lv/Er") - rb.state_fit(men, "Lv/Er")) < 1e-9
    assert rb.state_fit(som, "Lv/Er") > 0 > rb.state_fit(som, "I/A")


def test_contradiction_phrase_is_a_real_sentence():
    from output.phrase_builder import build_contradiction_phrase
    for d in (20, 60):
        for _ in range(20):
            out = build_contradiction_phrase(
                {"is_contradiction": True, "subject_label": "cow", "action_label": "fly"}, d)
            assert "not fly" not in out.lower() and "You not" not in out, out
            assert "cow" in out and out[0].isupper(), out
    assert build_contradiction_phrase(
        {"is_contradiction": True, "subject_label": "owl", "action_label": "walk on water"}, 20)


def test_engine_end_to_end_uses_bank_and_session_memory():
    from motors.cycle_manager_v5 import CycleManagerV5
    ccm = CycleManagerV5()
    outs = []
    for t in ["the guard raises his sword", "the wind blows through the street",
              "a stranger approaches with a lantern", "the stranger asks for shelter"]:
        outs.append(ccm.process(text=t)["verbal"])
    assert all(o and "{" not in o for o in outs), outs
    assert ccm._variant_memory, "the engine must remember the last variant used"
    # two engines = two memories (they don't step on each other between characters)
    assert CycleManagerV5()._variant_memory == {}


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
