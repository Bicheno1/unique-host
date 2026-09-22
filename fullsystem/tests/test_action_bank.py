# tests/test_action_bank.py — per-mode gesture bank (core/action_bank.py).
# Usage (from the project root):  python tests/test_action_bank.py
import os, sys, random, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core import action_bank as ab
from core import response_bank as rb
from core.response_matrix import RESPONSE_MATRIX

SUBJECTS = ["the bandit", "Mark", "that", "the bread", "you"]
LEANS = {"V/P", "I/A", "Lv/Er", "Gv/Rr"}


def _all_keys():
    keys = set()
    for cat, row in RESPONSE_MATRIX.items():
        for axis, verb in row.items():
            keys.add(rb.bank_key(verb, axis))
    return keys


def test_every_matrix_cell_has_an_action_bank_entry():
    missing = _all_keys() - set(ab.ACTION_BANK)
    assert not missing, missing
    extra = set(ab.ACTION_BANK) - _all_keys()
    assert not extra, extra


def test_bank_size_and_lean_variety():
    for key, variants in ab.ACTION_BANK.items():
        assert len(variants) >= 5, (key, len(variants))
        leans = {l for l, _ in variants}
        assert leans <= LEANS, (key, leans)
        assert len(leans) >= 3, (key, leans)
        texts = [t for _, t in variants]
        assert len(set(texts)) == len(texts), key  # no duplicates


def test_every_template_formats_for_every_subject():
    for key, variants in ab.ACTION_BANK.items():
        for _, t in variants:
            for s in SUBJECTS:
                out = t.format(subject=s, subject_cap=s[:1].upper() + s[1:])
                assert "{" not in out and "}" not in out, (key, t)
                assert out.strip(), (key, t)


def test_gestures_differ_from_the_literal_mode_name():
    # The whole point of this bank: at least some variants per mode must
    # NOT just be "{verb}ing {subject}" -- real synonyms/gestures, not
    # only the literal mode name re-conjugated.
    for key, variants in ab.ACTION_BANK.items():
        bare_verb = key.split("@")[0]
        non_literal = [t for _, t in variants if not t.lower().startswith(bare_verb.lower())]
        assert non_literal, (key, variants)


def test_render_action_from_bank_returns_none_for_unknown_mode():
    assert ab.render_action_from_bank("not_a_real_mode", "the bandit") is None


def test_render_action_from_bank_basic():
    out = ab.render_action_from_bank("attack", "the bandit", axis="Lv/Er", rng=random.Random(1))
    assert out and "{" not in out and "the bandit" in out


def test_user_speaker_subject_is_handled_like_any_other():
    # action_bank itself doesn't know about "user" -- that substitution
    # happens in cycle_manager_v5.py before calling it -- but it must
    # still format cleanly whatever subject string it's given, including "you".
    out = ab.render_action_from_bank("accept", "you", axis="V/P", rng=random.Random(1))
    assert out and "you" in out.lower()


def test_never_repeats_last_variant():
    rng = random.Random(7)
    for key in ab.ACTION_BANK:
        mem = {}
        last = None
        for _ in range(300):
            idx = rb.pick_variant(key, None, None, mem, rng, bank=ab.ACTION_BANK)
            assert idx != last, (key, idx)
            last = idx


def test_flat_profile_is_roughly_uniform():
    rng = random.Random(3)
    key = "observe"
    n = len(ab.ACTION_BANK[key])
    counts = [0] * n
    for _ in range(6000):
        counts[rb.pick_variant(key, None, None, None, rng, bank=ab.ACTION_BANK)] += 1
    assert min(counts) > 6000 / n * 0.75 and max(counts) < 6000 / n * 1.25, counts


def _gains(axis_short, high=9.0, low=2.0):
    return {c: {a: (high if a == axis_short else low) for a in ["V", "I", "Gv", "Lv"]}
            for c in ["danger", "benefit", "neutral", "unclassifiable"]}


def _share(key, lean, gains, n=4000):
    rng = random.Random(11)
    hits = 0
    for _ in range(n):
        idx = rb.pick_variant(key, gains, None, None, rng, bank=ab.ACTION_BANK)
        hits += ab.ACTION_BANK[key][idx][0] == lean
    return hits / n


def test_profile_shifts_choice_toward_matching_lean():
    for key in ("observe", "protect", "attack", "formulate"):
        composed  = _share(key, "Gv/Rr", _gains("Gv"))
        impulsive = _share(key, "Gv/Rr", _gains("Lv"))
        assert composed > impulsive + 0.10, (key, composed, impulsive)


def test_extreme_profile_never_zeroes_any_variant():
    for key in ab.ACTION_BANK:
        w = rb.variant_weights(key, _gains("Gv", 10.0, 0.0), None, bank=ab.ACTION_BANK)
        assert min(w) >= rb.MIN_WEIGHT and all(x > 0 for x in w), (key, w)


def test_action_and_dialogue_memories_are_independent():
    # Same key, two separate memory dicts (as cycle_manager_v5.py keeps
    # them) -- exercising one must not affect anti-repetition on the other.
    rng = random.Random(5)
    dlg_mem, act_mem = {}, {}
    for _ in range(50):
        rb.pick_variant("attack", None, None, dlg_mem, rng)
        rb.pick_variant("attack", None, None, act_mem, rng, bank=ab.ACTION_BANK)
    assert "attack" in dlg_mem and "attack" in act_mem


def test_engine_end_to_end_varies_the_action_line():
    from motors.cycle_manager_v5 import CycleManagerV5
    ccm = CycleManagerV5()
    actions = []
    for _ in range(12):
        out = ccm.process(text="a bandit steps out of the bushes, blade drawn")
        actions.append(out["action_text"])
    assert all(a and "{" not in a for a in actions), actions
    # with 6 attack-adjacent gestures and anti-repetition, 12 draws of the
    # same recurring mode should not all collapse to one literal string
    assert len(set(actions)) > 1, actions
    assert ccm._action_variant_memory, "the engine must remember the last gesture used"
    # two engines = two memories
    assert CycleManagerV5()._action_variant_memory == {}


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
