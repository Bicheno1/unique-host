
import random as _random
import re
import string

USE_CONSTRUCTION_FRAMES = True   # False -> core only (previous behavior)

# ── mode -> stance ───────────────────────────────────────────────────────
STANCE = {
    "attack": "urgent", "protect": "urgent", "flee": "urgent", "signal": "urgent",
    "accept": "open", "cooperate": "open", "investigate": "open",
    "deny": "closed", "ignore": "closed", "desist": "closed",
    "suppress": "closed", "surrender": "closed",
    "observe": "unsure", "group": "unsure", "formulate": "unsure",
}

# Probability that a frame is used when the family is detected. Questions
# and orders always get one (they ask for an answer); the rest vary so not
# every reply becomes two sentences.
FAMILY_PROBABILITY = {
    "yn_question": 1.0, "wh_question": 1.0, "imperative": 1.0, "warning": 1.0,
    "clause_lead": 0.85, "hypothetical": 0.7,
    "evaluative": 0.6, "existential": 0.5, "negation": 0.5, "passive": 0.5,
}

# ── THE BANK: key "frame:<family>:<stance|any>" -> [(lean, text), ...] ──
# `lean` has the same meaning as in response_bank.BANK (V/P warm, I/A dry,
# Lv/Er emotive, Gv/Rr measured) so the character's profile picks among
# variants with the same weighting the rest of the system uses.
FRAME_BANK = {
    # ── yes/no question ("Do you know him?") ─ answers without asserting facts
    "frame:yn_question:urgent": [
        ("Lv/Er", "No time for questions."), ("I/A", "Not now."),
        ("Gv/Rr", "Ask again once this is over."), ("V/P", "Questions can wait."),
    ],
    "frame:yn_question:open": [
        ("V/P", "Good question."), ("Gv/Rr", "Fair thing to ask."),
        ("Lv/Er", "Oh, that."), ("I/A", "Straight to the point."),
    ],
    "frame:yn_question:closed": [
        ("I/A", "No answer for that."), ("Lv/Er", "Please, no more questions."),
        ("Gv/Rr", "Not something to answer right now."), ("V/P", "Kindly, not that question."),
    ],
    "frame:yn_question:unsure": [
        ("Gv/Rr", "Hard to say."), ("I/A", "Maybe."),
        ("V/P", "Could be."), ("Lv/Er", "Hm. Depends."),
    ],
    # ── yes/no question whose object could be echoed ("Do you know him?" ->
    # "Him?"). Used instead of the plain yn_question bank when {echo} exists.
    # The bare "{echo}?" is one sentence, so it always fits the sentence cap.
    "frame:yn_echo:urgent": [
        ("Gv/Rr", "{echo}?"), ("Lv/Er", "{echo}? No time."),
        ("I/A", "{echo}? Not now."), ("V/P", "{echo}? Later."),
    ],
    "frame:yn_echo:open": [
        ("Gv/Rr", "{echo}?"), ("V/P", "{echo}? Good question."),
        ("Lv/Er", "{echo}? Oh, that."), ("I/A", "{echo}? Fair enough."),
    ],
    "frame:yn_echo:closed": [
        ("Gv/Rr", "{echo}?"), ("I/A", "{echo}? No answer for that."),
        ("Lv/Er", "{echo}? Please, no more."), ("V/P", "{echo}? Not that question."),
    ],
    "frame:yn_echo:unsure": [
        ("Gv/Rr", "{echo}?"), ("I/A", "{echo}? Maybe."),
        ("V/P", "{echo}? Could be."), ("Lv/Er", "{echo}? Hm. Depends."),
    ],
    # ── wh-question ("What is that noise?")  {wh} = What/Why/How/Where/Who...
    "frame:wh_question:urgent": [
        ("Lv/Er", "{wh}? No time."), ("I/A", "{wh}? Later."),
        ("Gv/Rr", "That question can wait."), ("V/P", "{wh}? Stay sharp first."),
    ],
    "frame:wh_question:open": [
        ("V/P", "{wh}? Worth asking."), ("Gv/Rr", "{wh}... Good thing to ask."),
        ("Lv/Er", "{wh}? Now that's something."), ("I/A", "{wh}? Go on."),
        ("I/A", "Fair question."),   # one-sentence option: fits cores that already have two
    ],
    "frame:wh_question:closed": [
        ("I/A", "{wh}? Nothing to say."), ("Lv/Er", "{wh}? Please, just leave it."),
        ("Gv/Rr", "That's not a question to answer now."), ("V/P", "{wh}? Some other time."),
    ],
    "frame:wh_question:unsure": [
        ("Gv/Rr", "{wh}? Still working it out."), ("I/A", "{wh}? Hard to say."),
        ("V/P", "{wh}... Good question."), ("Lv/Er", "{wh}? No idea, honestly."),
        ("I/A", "Not sure yet."),    # one-sentence option: fits cores that already have two
    ],
    # ── order ("Run!")
    "frame:imperative:urgent": [
        ("Lv/Er", "Yes!"), ("I/A", "Understood."),
        ("Gv/Rr", "Already moving."), ("V/P", "On it."),
    ],
    "frame:imperative:open": [
        ("V/P", "Of course."), ("Gv/Rr", "Understood."),
        ("Lv/Er", "Yes, right away!"), ("I/A", "Fine."),
    ],
    "frame:imperative:closed": [
        ("I/A", "Can't."), ("Lv/Er", "Not that. Anything but that."),
        ("Gv/Rr", "That can't be done right now."), ("V/P", "Not this time."),
    ],
    "frame:imperative:unsure": [
        ("Gv/Rr", "Noted."), ("I/A", "If that's the call."),
        ("V/P", "Maybe."), ("Lv/Er", "Hm. Fine."),
    ],
    # ── warning ("Watch out!", "Look out!", "Heads up!", "Careful!"): an alert, not
    # an order, so answering it with a refusal ("That can't be done") reads wrong.
    "frame:warning:urgent": [
        ("Lv/Er", "Seen it!"), ("I/A", "Seen."),
        ("Gv/Rr", "Already on it."), ("V/P", "Eyes open."),
    ],
    "frame:warning:open": [
        ("V/P", "Thanks for the warning."), ("Gv/Rr", "Good to know."),
        ("Lv/Er", "Oh! Thanks."), ("I/A", "Noted."),
    ],
    "frame:warning:closed": [
        ("I/A", "Not needed."), ("Lv/Er", "Please, don't say it like that."),
        ("Gv/Rr", "Understood. Not now."), ("V/P", "No need to shout."),
    ],
    "frame:warning:unsure": [
        ("Gv/Rr", "Noted."), ("I/A", "If so."),
        ("V/P", "Maybe."), ("Lv/Er", "Hm. Careful of what?"),
    ],
    # ── subject + adjective ("The bandit is dangerous.")  {adj_cap}/{adj}
    "frame:evaluative:urgent": [
        ("Lv/Er", "{adj_cap}! Yes."), ("I/A", "{adj_cap}. Obviously."),
        ("Gv/Rr", "{adj_cap}, and that's the problem."), ("V/P", "{adj_cap} indeed."),
    ],
    "frame:evaluative:open": [
        ("V/P", "{adj_cap}, yes."), ("Gv/Rr", "{adj_cap}, fair enough."),
        ("Lv/Er", "{adj_cap}! Really."), ("I/A", "{adj_cap}. Sure."),
    ],
    "frame:evaluative:closed": [
        ("I/A", "{adj_cap}. Doesn't change much."), ("Lv/Er", "{adj_cap}. Please, stop."),
        ("Gv/Rr", "{adj_cap}, perhaps. Not the point."), ("V/P", "{adj_cap}, maybe."),
    ],
    "frame:evaluative:unsure": [
        ("Gv/Rr", "{adj_cap}? Could be."), ("I/A", "{adj_cap}. Maybe."),
        ("V/P", "{adj_cap}... Hard to say."), ("Lv/Er", "{adj_cap}? Hm."),
    ],
    # ── existential ("There is a monster outside.")
    "frame:existential:urgent": [
        ("Lv/Er", "There! Seen it."), ("I/A", "Seen it."),
        ("Gv/Rr", "Already spotted."), ("V/P", "Eyes open."),
    ],
    "frame:existential:open": [
        ("V/P", "So there is."), ("Gv/Rr", "Worth a closer look."),
        ("Lv/Er", "Oh! Something's there."), ("I/A", "Noted."),
    ],
    "frame:existential:closed": [
        ("I/A", "Don't point it out."), ("Lv/Er", "Don't say it. Please."),
        ("Gv/Rr", "Better not to look."), ("V/P", "Best to look away."),
    ],
    "frame:existential:unsure": [
        ("Gv/Rr", "Something's there."), ("I/A", "Maybe."),
        ("V/P", "So it seems."), ("Lv/Er", "Hm. Something's there."),
    ],
    # ── negation ("I don't like this place.")
    "frame:negation:urgent": [
        ("Lv/Er", "No! Not like this."), ("I/A", "No."),
        ("Gv/Rr", "Not this time."), ("V/P", "Not here."),
    ],
    "frame:negation:open": [
        ("V/P", "Not necessarily."), ("Gv/Rr", "Fair enough."),
        ("Lv/Er", "Oh, no?"), ("I/A", "Fine. No."),
    ],
    "frame:negation:closed": [
        ("I/A", "Just as well."), ("Lv/Er", "No. No, no."),
        ("Gv/Rr", "Understood. No."), ("V/P", "No worries."),
    ],
    "frame:negation:unsure": [
        ("Gv/Rr", "Not necessarily."), ("I/A", "No, maybe."),
        ("V/P", "Perhaps not."), ("Lv/Er", "Hm, no?"),
    ],
    # ── passive ("The door was broken by the bandit.")
    "frame:passive:urgent": [
        ("Lv/Er", "Too late!"), ("I/A", "Already done."),
        ("Gv/Rr", "What's done is done."), ("V/P", "No undoing it now."),
    ],
    "frame:passive:open": [
        ("V/P", "So it was."), ("Gv/Rr", "What's done is done."),
        ("I/A", "Already done."), ("Lv/Er", "Oh. It was."),
    ],
    "frame:passive:closed": [
        ("I/A", "Done. Nothing to add."), ("Lv/Er", "Don't. Don't say what was done."),
        ("Gv/Rr", "Best left where it is."), ("V/P", "Let it rest."),
    ],
    "frame:passive:unsure": [
        ("Gv/Rr", "So it seems."), ("I/A", "Maybe."),
        ("V/P", "If that's how it happened."), ("Lv/Er", "Hm. Was it?"),
    ],
    # ── hypothetical ("If the bandit had moved...") — past what-if, any stance
    "frame:hypothetical:any": [
        ("Gv/Rr", "What might have been doesn't count now."), ("I/A", "Too late for what-ifs."),
        ("V/P", "No use wondering."), ("Lv/Er", "Don't. No what-ifs."),
    ],
    # ── clause lead: If / When / Although / Because ... X, ...   {lead}
    # The input's own subordinate clause is echoed and the reply is built
    # around it. {core_lc} variants join mid-sentence (need a joinable core).
    # Every variant reads correctly for if/when/although/because/unless...
    "frame:clause_lead:any": [
        ("Gv/Rr", "{lead}, {core_lc}"), ("V/P", "{lead} — heard. {core}"),
        ("Lv/Er", "{lead}, all right. {core}"), ("I/A", "{lead}, fine. {core}"),
    ],
    # Used instead when the input's clause could not be echoed safely
    # (too long, or it contains 1st/2nd person words).
    "frame:clause_lead_plain:any": [
        ("Gv/Rr", "Noted."), ("V/P", "Heard."),
        ("Lv/Er", "Fine, fine."), ("I/A", "So be it."),
    ],
}

_FORMATTER = string.Formatter()
_AUX_START = {"do", "does", "did", "is", "are", "was", "were", "can", "could", "will",
              "would", "should", "have", "has", "had", "may", "might", "must"}
_WH_TAGS = {"WP", "WRB", "WDT", "WP$"}
_LEAD_MARKS = {"if", "when", "while", "although", "though", "because", "since",
               "once", "unless", "before", "after", "as", "until"}
_PERSONAL = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours",
             "you", "your", "yours", "yourself", "'m", "'re", "'ve"}
_CLAUSE_LABELS = {"CONDITIONAL", "TEMPORAL", "CONCESSIVE", "CAUSAL"}
_JOINABLE = re.compile(r"^(We|You|They|I)\b")


# ── detection ────────────────────────────────────────────────────────────
def _find_lead(doc):
    """Text of the first subordinate clause opened by a real conjunction
    (if/when/although...), or None. Skipped when the clause contains 1st/2nd
    person words: echoing those needs pronoun reflection and the voice of the
    reply differs by axis, so no echo is safer than a wrong one."""
    for tok in doc:
        if tok.dep_ != "advcl":
            continue
        if not any(c.dep_ == "mark" and c.lower_ in _LEAD_MARKS for c in tok.children):
            continue
        span = doc[tok.left_edge.i: tok.right_edge.i + 1]
        if len(span) > 9 or any(t.lower_ in _PERSONAL for t in span):
            continue
        text = span.text.strip(" ,;:.!?")
        if text:
            return text[:1].upper() + text[1:]
    return None


def _find_adjective(doc):
    for tok in doc:
        if tok.dep_ in ("acomp", "attr") and tok.pos_ == "ADJ":
            return tok.lower_
    return None


_ECHO_PRONOUNS = {"him": "Him", "her": "Her", "them": "Them", "it": "It",
                  "that": "That", "this": "This"}
# Words whose echo would need person reflection (me -> you...): no echo at all.
_NO_ECHO = {"you", "your", "yours", "yourself", "me", "my", "mine", "myself",
            "i", "we", "us", "our", "ours"}


def _find_echo(sent):
    """What a yes/no question is ABOUT, to repeat back ELIZA-style:
    'Do you know him?' -> 'Him', 'Is the bandit dead?' -> 'Dead'. Looks at the
    main verb's object / attribute / complement (then a prepositional
    object). None when nothing safe is there (only 'you'/'me' words, more
    than 4 words, or no object)."""
    root = sent.root
    cands = [c for c in root.children if c.dep_ in ("dobj", "attr", "acomp", "oprd")]
    for c in root.children:
        if c.dep_ in ("prep", "dative"):
            cands += [g for g in c.children if g.dep_ == "pobj"]
    for tok in cands:
        low = tok.lower_
        if low in _NO_ECHO or tok.tag_ in _WH_TAGS:
            continue
        if low in _ECHO_PRONOUNS:
            return _ECHO_PRONOUNS[low]
        if tok.pos_ in ("NOUN", "PROPN", "ADJ"):
            span = sent.doc[tok.left_edge.i: tok.i + 1]
            words = [t for t in span if not t.is_punct]
            if len(words) > 4 or any(t.lower_ in _NO_ECHO for t in words):
                continue
            text = span.text.strip()
            if text:
                return text[:1].upper() + text[1:]
    return None


def _question_kind(doc):
    """('wh'|'yn'|None, wh-word, sentence). A '?' ending decides; without one,
    an auxiliary-first inversion ('Do you know him') counts as yes/no."""
    sents = list(doc.sents)
    for sent in reversed(sents):
        toks = [t for t in sent if not t.is_space]
        if not toks:
            continue
        head = toks[:3]
        wh = next((t for t in head if t.tag_ in _WH_TAGS), None)
        if sent.text.strip().endswith("?"):
            return ("wh", wh.lower_, sent) if wh else ("yn", None, sent)
        if (toks[0].lower_ in _AUX_START and len(toks) > 1
                and toks[1].pos_ in ("PRON", "PROPN", "NOUN", "DET")):
            return ("yn", None, sent)
    return (None, None, None)


_WARNING_PAIRS = {("watch", "out"), ("look", "out"), ("heads", "up")}
_WARNING_WORDS = {"careful", "beware"}


def _is_warning(doc):
    """'Watch out!', 'Look out!', 'Heads up!', 'Careful!', 'Beware!' at the start
    of a sentence. 'Look at the bandit!' is an order, not a warning."""
    for sent in doc.sents:
        toks = [t.lower_ for t in sent if not t.is_punct and not t.is_space]
        if toks and (toks[0] in _WARNING_WORDS or tuple(toks[:2]) in _WARNING_PAIRS):
            return True
    return False


def detect_family(doc, constructions):
    """(family, slots) for the input, or (None, {}) when nothing frames it.
    Priority: question > warning > order > clause/hypothetical > adjective >
    existential > passive > negation."""
    constructions = constructions or []
    kind, wh, qsent = _question_kind(doc)
    if kind == "wh":
        return "wh_question", {"wh": wh.capitalize()}
    if kind == "yn":
        return "yn_question", {"echo": _find_echo(qsent)}
    if _is_warning(doc):
        return "warning", {}
    if "IMPERATIVE" in constructions:
        return "imperative", {}
    if "HYPOTHETICAL" in constructions:
        return "hypothetical", {}
    if any(c in _CLAUSE_LABELS for c in constructions):
        return "clause_lead", {"lead": _find_lead(doc)}
    if "EVALUATIVE" in constructions:
        adj = _find_adjective(doc)
        if adj:
            return "evaluative", {"adj": adj, "adj_cap": adj.capitalize()}
    if "EXISTENTIAL" in constructions:
        return "existential", {}
    if "PASSIVE_VOICE" in constructions:
        return "passive", {}
    if "NEGATION" in constructions:
        return "negation", {}
    return None, {}


# ── composition ──────────────────────────────────────────────────────────
def _core_lc(core: str):
    """Core with its first letter lowercased, only when that is safe
    (starts with We/You/They/I). None otherwise."""
    if not _JOINABLE.match(core):
        return None
    return core if core.startswith("I") else core[:1].lower() + core[1:]


_SENT = re.compile(r"[^.!?]+(?:[.!?]+|$)")
MAX_SENTENCES = 3          # frame + core never exceed this (questions/orders may reach 4 as a last resort)
_FRAGMENT_MAX_WORDS = 4    # "Steady." / "Too much, too soon." / "Everyone, listen."


def _sentences(text: str):
    return [m.group(0).strip() for m in _SENT.finditer(text) if m.group(0).strip()]


def _is_fragment(sentence: str) -> bool:
    """A short opener with no subject pronoun ('Steady.', 'Fine.', 'Everyone,
    listen.'). 'We keep still.' is a real clause, not a fragment."""
    return (len(re.findall(r"[\w']+", sentence)) <= _FRAGMENT_MAX_WORDS
            and not _JOINABLE.match(sentence))


_DANGLING_END = re.compile(r"\b(what|how|why|who|where|when|which|and|but|or|to|of|the|a|an)[.!?]*$", re.I)


def _strip_leading_fragments(core: str, subject: str = None) -> str:
    """Drops the core's leading interjections/fragments while at least one
    real sentence remains. Used ONLY when a frame goes in front: the frame
    already plays that role, and stacking both is what read as a pile of
    fragments ('Brave! Really. Steady. We open right up.').

    Two guards (found 2026-09-23 auditing response_bank.BANK):
      * a sentence that names the reply's TARGET is content, not an
        interjection -- never dropped ('Something's off about you. We find
        out what.' must not lose its first half; 'Heads up -- watch you.'
        is the point of the line);
      * never strip if what remains would end dangling ('... find out what.').
    """
    sents = _sentences(core)
    subj = (subject or "").strip().lower()
    if subj == "user":
        subj = "you"
    i = 0
    while i < len(sents) - 1 and _is_fragment(sents[i]) and not (subj and subj in sents[i].lower()):
        i += 1
    if not i:
        return core
    rest = " ".join(sents[i:])
    return core if _DANGLING_END.search(rest) else rest


def _fields(text: str):
    return {f for _, f, _, _ in _FORMATTER.parse(text) if f}


def _pick(key, values, gains, state, memory, rng, cap=None):
    """Weighted draw among the variants whose slots all have a value and
    that keep the whole reply within MAX_SENTENCES, excluding the last one
    used for this key (same anti-repetition as response_bank.pick_variant,
    plus the slot-availability and length filters)."""
    from core.response_bank import variant_weights
    weights = variant_weights(key, gains, state, bank=FRAME_BANK)
    for i, (_, text) in enumerate(FRAME_BANK[key]):
        if any(values.get(f) is None for f in _fields(text)):
            weights[i] = 0.0
            continue
        total = len(_sentences(text.format(**values)))
        if "{core" not in text:
            total += len(_sentences(values["core"]))
        if total > (MAX_SENTENCES if cap is None else cap):
            weights[i] = 0.0
    last = memory.get(key) if memory is not None else None
    if last is not None and 0 <= last < len(weights) and sum(w > 0 for w in weights) > 1:
        weights[last] = 0.0
    if sum(weights) <= 0:
        return None
    idx = rng.choices(range(len(weights)), weights=weights, k=1)[0]
    if memory is not None:
        memory[key] = idx
    return idx


def apply_frame(core: str, mode: str, doc, constructions, gains=None, state=None,
                memory=None, rng=None, subject: str = None):
    """Returns (sentence, family). `family` is None when no frame was used
    (and then the reply is `core` exactly as given). When a frame IS used,
    the core's leading fragments are dropped (see _strip_leading_fragments)
    and its first letter is lowercased only for {core_lc} joins; the core's
    real clauses are never rewritten."""
    if not USE_CONSTRUCTION_FRAMES or not core or doc is None:
        return core, None
    rng = rng or _random
    family, slots = detect_family(doc, constructions)
    if not family:
        return core, None
    if rng.random() >= FAMILY_PROBABILITY.get(family, 0.5):
        return core, None
    stance = STANCE.get(mode)
    must_frame = FAMILY_PROBABILITY.get(family, 0.0) >= 1.0   # questions and orders
    if family == "clause_lead" and slots.get("lead") is None:
        family = "clause_lead_plain"
    if family == "yn_question" and slots.get("echo"):
        family = "yn_echo"
    key = f"frame:{family}:{stance}"
    if key not in FRAME_BANK:
        key = f"frame:{family}:any"
    if key not in FRAME_BANK:
        return core, None
    body = _strip_leading_fragments(core, subject)
    values = dict(slots, core=body, core_lc=_core_lc(body))
    idx = _pick(key, values, gains, state, memory, rng)
    if idx is None and must_frame:
        # A question/order must be answered even when the core is already
        # 3 sentences: one extra sentence, only as a last resort.
        idx = _pick(key, values, gains, state, memory, rng, cap=MAX_SENTENCES + 1)
    if idx is None:
        return core, None
    text = FRAME_BANK[key][idx][1]
    out = text.format(**values)
    if "{core" not in text:
        out = f"{out} {body}"
    return out, family
