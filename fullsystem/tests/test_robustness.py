# tests/test_robustness.py — odd inputs must never crash a turn or produce broken text
# (construction frames + topic target + full cycle). Usage: python tests/test_robustness.py
import os, sys, json, random, re, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "displayer"))

from core.construction_matcher import analyze_input
from core import construction_frames as cf, topic_target as tt
from core.response_matrix import select_axis_response, RESPONSE_MATRIX

ODD = [
    "", " ", "...", "?!", "?", "\n\n", "\t", "a", "I", "the", "DELIA!!!", "WHAT IS THAT NOISE???",
    "😀😀😀", "¿Qué es ese ruido?", "El bandido es peligroso.", "12345", "http://example.com/a?b=c",
    "<<", ">>", "<<>>", "<<unclosed action", '"Angry" ', '"Angry" Get out! <<slams the door>>',
    "*draws sword*", "Delia, Delia, Delia?", "Why? Why? Why?", "If if if if", "Although", "Do you",
    "Is", "What", "There is", "There.", "Not.", "Run run run run run!", "The the the bandit bandit.",
    "x" * 3000, "The bandit is dangerous. " * 60, "Do you know " + "him and " * 40 + "her?",
    "You you you you.", "Him?", "Because.", "He said she said they said it was done by them.",
    "The bandit was killed.", "Killed by whom?", "Don't.", "Never!", "Is he dead or alive?",
    "Who? What? Where?", "Joaquin: Watch out!", "Ünïcödé bändït is dängerous.",
    "{subject} {mode} {pronoun}", "{}", "%s %d", "\\", "'\"'",
    # constructions the first fuzz set did not reach
    "If the bandit moves, we are dead.", "Although it's dark, we must go.", "If you move, I shoot.",
    "If the bandit had moved, it would be over.", "When the sun sets, the wolves come out.",
    "Because the bridge fell, we are stuck.", "If", "If, then.", "Unless you run, you die.",
    "If the bandit moves and the wolf howls and the door opens and the roof falls, we run.",
]
SPEAKERS = [None, "user", "Joaquin", "the bandit"]
CELLS = [(c, a) for c, row in RESPONSE_MATRIX.items() for a in row]


def _defects(s):
    out = []
    if not isinstance(s, str) or not s.strip():
        return ["empty"]
    if "{" in s or "}" in s: out.append("braces")
    if "None" in s: out.append("None")
    if "  " in s: out.append("double space")
    if re.search(r"\s[,.;:!?]", s): out.append("space before punctuation")
    if re.search(r"\?\?|,,|\.\.\.\.", s): out.append("doubled punctuation")
    if re.search(r"[.!?]\s+[a-z]", s): out.append("lowercase after full stop")
    return out


def test_layers_never_raise_without_the_safety_net():
    # The try/except in select_axis_response would hide a bug in the new layers;
    # here they are called directly.
    for t in ODD:
        parsed = analyze_input(t, "Delia") if t else {"subject": None, "constructions": []}
        for fx in SPEAKERS:
            tt.pick_target(parsed, fx, "Delia")
        if parsed.get("doc") is None:
            continue
        for mode in cf.STANCE:
            for seed in range(2):
                out, fam = cf.apply_frame("We attack the bandit. Nothing more.", mode, parsed["doc"],
                                          parsed["constructions"], rng=random.Random(seed))
                assert isinstance(out, str) and out.strip()


def test_generated_replies_are_well_formed():
    rng = random.Random(1)
    for t in ODD:
        for fx in SPEAKERS:
            for c, a in rng.sample(CELLS, 6):
                r = select_axis_response(a, c, "Delia", raw_text=t, forced_focus=fx, rng=random.Random(5))
                d = _defects(r["sentence"])
                assert not d, (t[:40], fx, a, c, d, r["sentence"])
                if r["frame_family"]:
                    must = r["frame_family"] in ("yn_question", "yn_echo", "wh_question", "imperative", "warning")
                    assert len(cf._sentences(r["sentence"])) <= cf.MAX_SENTENCES + (1 if must else 0), r["sentence"]


def test_same_seed_same_reply():
    for t in ("What is that noise?", "If the bandit moves, we are dead.", "Do you know him?", "Run!"):
        a = select_axis_response("V/P", "danger", "Delia", raw_text=t, forced_focus="user", rng=random.Random(9))
        b = select_axis_response("V/P", "danger", "Delia", raw_text=t, forced_focus="user", rng=random.Random(9))
        assert a["sentence"] == b["sentence"]


def test_long_session_with_shared_variant_memory():
    mem = {}
    seen = []
    for i in range(300):
        t = ODD[i % len(ODD)]
        r = select_axis_response(*(lambda ca: (ca[1], ca[0]))(CELLS[i % len(CELLS)]), "Delia", raw_text=t,
                                 forced_focus="user", rng=random.Random(i), variant_memory=mem)
        assert not _defects(r["sentence"]), (t[:40], r["sentence"])
        seen.append(r["sentence"])
    assert len(set(seen)) > 40      # not collapsing to a handful of phrases


def test_full_cycle_survives_odd_input_with_every_speaker():
    import app
    from core.marker_parser import parse_marked_input as P
    delia = os.path.join(HERE, "..", "..", "fullcompiler", "characters", "delia_adventurer_v4.json")
    for sp in ("narrator", "user", "Joaquin", "bandit"):
        random.seed(3)
        ccm, _ = app.inject_character(json.load(open(delia)))
        for t in ODD:
            mo = ccm.process(text="", marked_input=P(t), speaker=sp)["marked_output"]
            assert isinstance(mo, str) and mo.strip(), (sp, t[:40])
            assert "{" not in mo and "}" not in mo and "None" not in mo, (sp, t[:40], mo)


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("ok  ", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e)[:400])
    print("\n%s" % ("ALL OK" if not fails else f"{fails} FAILED"))
    sys.exit(1 if fails else 0)
