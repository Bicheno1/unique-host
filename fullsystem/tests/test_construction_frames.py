# tests/test_construction_frames.py — construction frames (core/construction_frames.py).
# Usage (from the project root):  python tests/test_construction_frames.py
import os, sys, re, random, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core import construction_frames as cf
from core.construction_matcher import analyze_input
from core.response_matrix import RESPONSE_MATRIX, select_axis_response

STANCES = {"urgent", "open", "closed", "unsure"}
FAMILIES = set(cf.FAMILY_PROBABILITY) | {"clause_lead_plain", "yn_echo"}
SLOTS = {"lead", "adj", "adj_cap", "wh", "echo", "core", "core_lc"}
LEANS = {"V/P", "I/A", "Lv/Er", "Gv/Rr"}

SAMPLES = {
    "The bandit is dangerous.": "evaluative",
    "You are brave and fast.": "evaluative",
    "If the bandit moves, we are dead.": "clause_lead",
    "Although it's dark, we must go.": "clause_lead",
    "If the bandit had moved, it would be over.": "hypothetical",
    "What is that noise?": "wh_question",
    "Why did you run away?": "wh_question",
    "Do you know him?": "yn_question",
    "Run!": "imperative",
    "Watch out Delia, a bandit!": "warning",
    "Look out!": "warning",
    "Look at the bandit!": "imperative",   # an order to look, not a warning
    "The door was broken by the bandit.": "passive",
    "There is a monster outside.": "existential",
    "I don't like this place.": "negation",
}


def _parse(text):
    r = analyze_input(text, "Delia")
    return r["doc"], r["constructions"]


def test_every_mode_has_a_stance():
    modes = {verb for row in RESPONSE_MATRIX.values() for verb in row.values()}
    assert modes <= set(cf.STANCE), modes - set(cf.STANCE)
    assert set(cf.STANCE.values()) <= STANCES


def test_bank_covers_every_family_and_stance():
    for fam in FAMILIES:
        for st in STANCES:
            assert f"frame:{fam}:{st}" in cf.FRAME_BANK or f"frame:{fam}:any" in cf.FRAME_BANK, (fam, st)
    for key in cf.FRAME_BANK:
        _, fam, st = key.split(":")
        assert fam in FAMILIES and (st in STANCES or st == "any"), key


def test_bank_shape_and_uniqueness():
    for key, variants in cf.FRAME_BANK.items():
        texts = [t for _, t in variants]
        assert len(set(texts)) == len(texts), key
        assert len(variants) >= 3, key
        assert {l for l, _ in variants} <= LEANS, key
        for t in texts:
            assert cf._fields(t) <= SLOTS, (key, t)


def test_frames_have_no_personal_pronouns_or_be_forms():
    # The core's voice (We/You/I/They) changes with the axis: a frame in a
    # fixed person would break agreement with it.
    bad = re.compile(r"\b(I|me|my|we|us|our|you|your|they|them|their|am|are)\b|'m\b|'re\b", re.I)
    for key, variants in cf.FRAME_BANK.items():
        for _, t in variants:
            plain = re.sub(r"\{[a-z_]+\}", "", t)
            assert not bad.search(plain), (key, t)


def test_detection_of_input_constructions():
    for text, expected in SAMPLES.items():
        doc, cons = _parse(text)
        fam, _ = cf.detect_family(doc, cons)
        assert fam == expected, (text, cons, fam)


def test_plain_declarative_gets_no_frame():
    doc, cons = _parse("The bandit is here.")
    assert cf.detect_family(doc, cons)[0] is None
    out, fam = cf.apply_frame("We attack the bandit.", "attack", doc, cons, rng=random.Random(1))
    assert (out, fam) == ("We attack the bandit.", None)


def test_questions_and_orders_are_always_framed_and_core_kept_intact():
    core = "Steady. We attack you together, and we finish it."
    for text in ("What is that noise?", "Do you know him?", "Run!", "Watch out Delia, a bandit!"):
        doc, cons = _parse(text)
        for seed in range(30):
            out, fam = cf.apply_frame(core, "attack", doc, cons, rng=random.Random(seed))
            assert fam and out != core and out.endswith("We attack you together, and we finish it."), (text, seed, out)
            assert "Steady." not in out, out   # the core's leading fragment yields to the frame


def test_clause_lead_echoes_the_input_clause():
    doc, cons = _parse("If the bandit moves, we are dead.")
    seen = set()
    for seed in range(40):
        out, fam = cf.apply_frame("We attack the bandit.", "attack", doc, cons, rng=random.Random(seed))
        if fam:
            assert out.startswith("If the bandit moves"), out
            seen.add(out)
    assert len(seen) >= 3, seen


def test_clause_lead_skips_echo_with_personal_pronouns():
    doc, cons = _parse("If you move, we are dead.")
    for seed in range(40):
        out, fam = cf.apply_frame("We attack the bandit.", "attack", doc, cons, rng=random.Random(seed))
        assert "you move" not in out.lower(), out


def test_unjoinable_core_never_gets_a_mid_sentence_join():
    doc, cons = _parse("If the bandit moves, we are dead.")
    for seed in range(60):
        out, fam = cf.apply_frame("Steady. Hold the line.", "protect", doc, cons, rng=random.Random(seed))
        assert ", steady" not in out.lower() and ", hold" not in out.lower() and out.endswith("Hold the line."), out


def test_stance_keeps_tone_consistent_with_the_mode():
    # closed modes must never open with an accepting frame, and vice versa
    doc, cons = _parse("Do you know him?")
    accepting = {t for _, t in cf.FRAME_BANK["frame:yn_question:open"]}
    refusing = {t for _, t in cf.FRAME_BANK["frame:yn_question:closed"]}
    for seed in range(40):
        out, _ = cf.apply_frame("They turn you away.", "deny", doc, cons, rng=random.Random(seed))
        assert not any(out.startswith(t) for t in accepting), out
        out, _ = cf.apply_frame("We welcome you.", "accept", doc, cons, rng=random.Random(seed))
        assert not any(out.startswith(t) for t in refusing), out


def test_same_reaction_different_construction_gives_different_reply():
    replies = set()
    for text in SAMPLES:
        r = select_axis_response("V/P", "danger", "Delia", raw_text=text,
                                 forced_focus="user", rng=random.Random(7))
        replies.add(r["sentence"])
        assert cf._sentences(r["core_sentence"])[-1] in r["sentence"]
    assert len(replies) >= 8, len(replies)


def test_flag_off_restores_previous_behavior():
    cf.USE_CONSTRUCTION_FRAMES = False
    try:
        for text in SAMPLES:
            r = select_axis_response("V/P", "danger", "Delia", raw_text=text,
                                     forced_focus="user", rng=random.Random(7))
            assert r["sentence"] == r["core_sentence"] and r["frame_family"] is None
    finally:
        cf.USE_CONSTRUCTION_FRAMES = True


def test_investigate_reflection_is_not_framed_twice():
    for seed in range(20):
        r = select_axis_response("V/P", "unclassifiable", "Delia", raw_text="Why did you run away?",
                                 forced_focus="user", rng=random.Random(seed))
        assert r["verb"] == "investigate"
        assert r["frame_family"] is None and r["sentence"] == r["core_sentence"]


def test_questions_and_orders_are_framed_for_every_cell_and_seed():
    # The sentence cap must never be the reason a question/order goes
    # unanswered: every stance has at least one variant that fits any core.
    cells = [(c, a) for c, row in RESPONSE_MATRIX.items() for a in row]
    for i, text in enumerate(("What is that noise?", "Why did you run away?", "Do you know him?", "Run!",
                              "Watch out Delia, a bandit!")):
        for c, a in cells:
            for seed in range(4):
                r = select_axis_response(a, c, "Delia", raw_text=text, forced_focus="user",
                                         rng=random.Random(seed * 7 + i))
                if r["verb"] == "investigate" and r["frame_family"] is None:
                    continue   # already a reflected question
                assert r["frame_family"], (text, r["verb"], r["core_sentence"])


def test_a_warning_is_never_answered_with_a_refusal():
    doc, cons = _parse("Watch out Delia, a bandit!")
    refusals = {"Can't.", "That can't be done right now.", "Not this time.", "Not that. Anything but that."}
    for mode in cf.STANCE:
        for seed in range(20):
            out, fam = cf.apply_frame("We hit the bandit first.", mode, doc, cons, rng=random.Random(seed))
            assert fam == "warning" and not any(out.startswith(r) for r in refusals), (mode, out)


def test_strip_leading_fragments():
    f = cf._strip_leading_fragments
    assert f("Steady. We attack you together, and we finish it.") == "We attack you together, and we finish it."
    assert f("Too much, too soon. They push you back.") == "They push you back."
    assert f("Everyone, listen. You could be trouble.") == "You could be trouble."
    assert f("We keep still. Nothing more.") == "We keep still. Nothing more."   # opens with a real clause
    assert f("Fine.") == "Fine."                                                # never strips to empty
    assert f("Steady. Hold the line.") == "Hold the line."


def test_strip_never_drops_a_sentence_that_names_the_target():
    f = cf._strip_leading_fragments
    assert f("Something's off about you. We find out what.", "user") == "Something's off about you. We find out what."
    assert f("Heads up — watch Joaquin. Pass the word.", "Joaquin") == "Heads up — watch Joaquin. Pass the word."
    assert f("Steady. We attack the bandit.", "the bandit") == "We attack the bandit."   # fragment without the target still goes


def test_strip_over_the_whole_bank_never_leaves_broken_text():
    from core import response_bank as rb
    for subj in ("you", "that", "Joaquin", "the noise", "the bandit"):
        for key, variants in rb.BANK.items():
            for _, t in variants:
                for pron in ("We", "You", "I", "They"):
                    out = t.format(subject=subj, subject_cap=subj[:1].upper() + subj[1:], mode="observe",
                                   pronoun=pron, pronoun_lower=("I" if pron == "I" else pron.lower()))
                    st = cf._strip_leading_fragments(out, subj)
                    assert not cf._DANGLING_END.search(st) or cf._DANGLING_END.search(out), (key, out, st)
                    if subj.lower() in out.lower():
                        assert subj.lower() in st.lower(), (key, out, st)   # the target never disappears


def test_reply_never_exceeds_the_sentence_cap():
    cells = [(c, a) for c, row in RESPONSE_MATRIX.items() for a in row]
    for i, text in enumerate(SAMPLES):
        for c, a in cells:
            for seed in range(3):
                r = select_axis_response(a, c, "Delia", raw_text=text, forced_focus="user",
                                         rng=random.Random(seed * 7 + i))
                if r["frame_family"]:
                    must = r["frame_family"] in ("yn_question", "yn_echo", "wh_question", "imperative", "warning")
                    limit = cf.MAX_SENTENCES + (1 if must else 0)   # questions/orders: 1 extra as last resort
                    assert len(cf._sentences(r["sentence"])) <= limit, (text, r["sentence"])


def test_unframed_reply_keeps_its_core_exactly():
    for i, text in enumerate(SAMPLES):
        for seed in range(10):
            r = select_axis_response("V/P", "danger", "Delia", raw_text=text, forced_focus="user",
                                     rng=random.Random(seed))
            if not r["frame_family"]:
                assert r["sentence"] == r["core_sentence"]


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
