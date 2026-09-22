# core/response_bank.py — UNIQUE HOST
#
# PER-MODE PHRASE BANK + PROFILE-BASED SELECTION
# ══════════════════════════════════════════════════════════════
# Replaces MODE_TEMPLATES (core/construction_matcher.py) as the source
# of the sentence the player reads. MODE_TEMPLATES still exists as a
# fallback (render_mode_template) but is no longer the first option.
#
# WHY (real test, 100 turns, default character): 31 distinct
# sentences, one of them in 20 % of the turns, and several sounded like a
# system label ("I formulate it anyway"). Causes: 2 variants per
# mode, uniform randomness with no memory, and the mode name used as a spoken
# verb.
#
# HOW IT WORKS
#   1. The MODE was already decided by the matrix (category × axis). This does not touch it.
#   2. Each mode has 5-6 variants. ALL of them mean the same thing (same
#      response function, defined in chemical_system_physiological_
#      effects.md); only the nuance of expression changes.
#   3. Each variant carries a `lean` tag: which axis its expression
#      nuance leans toward, independent of the mode's axis:
#         "V/P"   -> warm, open, engaged
#         "I/A"   -> dry, flat, withdrawn, terse
#         "Lv/Er" -> emotive, impulsive, personal
#         "Gv/Rr" -> measured, composed, reasoned
#   4. Weight of each variant = 1 + A*profile_fit + B*state_fit
#         profile_fit: the character's gains (stable personality)
#                       for the `lean` axis, averaged over the 4
#                       categories: (mean-5)/5, in [-1, 1].
#         state_fit: how much the `lean` axis weighs in the current state of the
#                       dominant engine (the moment): share - 0.25.
#      WEIGHTED draw (the highest score does not simply win: that would always repeat
#      the same sentence for a given character) and the last
#      variant used in that mode is excluded (anti-repetition).
#   5. Flat profile (all 5) => roughly equal weights => what remains is random with
#      anti-repetition. This is the expected behavior of the default
#      character or of one with unanswered sections.
#
# WRITING RULES (why the sentences look the way they do)
#   * The pronoun is fixed by the mode's axis (SOCIAL_POSITIONING, author's
#     decision): V/P=We, Gv/Rr=You, Lv/Er=I, I/A=They. That is why the sentences use
#     {pronoun}/{pronoun_lower} + base-form verbs (I/we/you/they
#     share the form) and do NOT use am/are/'m/'re, nor possessives (my/your/our),
#     nor reflexives. Contractions with 've and 'll are fine for all 4.
#   * {mode} is only used where the mode's verb sounds natural without a
#     preposition (attack, accept, deny, observe, investigate, flee).
#   * Since the subject can be a person or an object ("the merchant"/"the
#     bread"), "it" referring to the subject is avoided.
#   * {subject} can be "the bandit", "Mark", "that" or "you" (the "user"
#     speaker arrives bare from speaker_to_focus and is read here as "you"):
#     so a 3rd-person verb (-s, is, has, does) NEVER goes right
#     after the subject; only past tense, modals, won't/can't or infinitive.
#
# To edit: add/remove (lean, text) tuples in BANK. test_response_bank
# validates format, pronoun agreement, anti-repetition and the effect of the
# profile.

import random as _random

USE_RESPONSE_BANK = True   # False -> goes back to MODE_TEMPLATES (old fallback)

# Formula weights. A: personality (gains). B: the moment (state).
PROFILE_WEIGHT = 1.5
STATE_WEIGHT   = 2.0
MIN_WEIGHT     = 0.1

_SHORT = {"V/P": "V", "I/A": "I", "Lv/Er": "Lv", "Gv/Rr": "Gv"}
_MENTAL = {"V/P": "P", "I/A": "A", "Lv/Er": "Er", "Gv/Rr": "Rr"}

# ── THE BANK ────────────────────────────────────────────────────────────
BANK = {
    # ── danger ─────────────────────────────────────────── (V/P = We)
    "attack": [
        ("Lv/Er", "{pronoun} tear into {subject} — no holding back."),
        ("Gv/Rr", "Steady. {pronoun} {mode} {subject} together, and {pronoun_lower} finish it."),
        ("V/P",   "{pronoun} {mode} {subject} and {pronoun_lower} don't back down."),
        ("I/A",   "Enough. {pronoun} {mode} {subject}."),
        ("V/P",   "{subject_cap} started this. {pronoun} end it."),
        ("Lv/Er", "{pronoun} hit {subject} first, and {pronoun_lower} hit hard."),
    ],
    # ── I/A = They
    "surrender": [
        ("I/A",   "There's nothing left to fight with. {pronoun} let {subject} come."),
        ("I/A",   "{pronoun} stop. {subject_cap} can have the rest."),
        ("Lv/Er", "Too much, too fast — {pronoun_lower} can't hold {subject} back anymore."),
        ("Gv/Rr", "No point pretending. {pronoun} give in to {subject}."),
        ("V/P",   "{pronoun} lower everything and let {subject} take whatever comes."),
    ],
    # ── Gv/Rr = You
    "protect": [
        ("Gv/Rr", "{pronoun} stay back. {subject_cap} won't get past."),
        ("V/P",   "{pronoun} keep close and keep quiet. {subject_cap} won't touch anyone."),
        ("I/A",   "{pronoun} hold the line here. {subject_cap} won't get any further."),
        ("Lv/Er", "Get back! {pronoun} shield the others while {pronoun_lower} can."),
        ("Gv/Rr", "Because {subject} won't stop, {pronoun_lower} stay behind me."),
        ("V/P",   "{pronoun} don't need to worry. I've got {subject}."),
    ],
    # ── Lv/Er = I
    "flee": [
        ("Lv/Er", "{pronoun} can't stay. {subject_cap} won't wait — {pronoun_lower} run."),
        ("I/A",   "Move. {pronoun} {mode} {subject}, now."),
        ("Gv/Rr", "{pronoun} know when to leave, and this is it. {pronoun} get away from {subject}."),
        ("V/P",   "Not like this. {pronoun} get out, and {pronoun_lower} come back for the rest."),
        ("Lv/Er", "Out! {pronoun} need to be anywhere but near {subject}."),
    ],
    # ── benefit ────────────────────────────────────────── (V/P = We)
    "accept": [
        ("V/P",   "{pronoun} welcome {subject}. Gladly."),
        ("Gv/Rr", "That's fair. {pronoun} say yes to {subject}."),
        ("Lv/Er", "{pronoun} open right up to {subject}."),
        ("I/A",   "Fine. {pronoun} {mode} {subject}."),
        ("V/P",   "It feels right — {pronoun_lower} go with {subject}."),
    ],
    # ── I/A = They
    "deny": [
        ("I/A",   "{pronoun} turn {subject} away — there's no room left."),
        ("Lv/Er", "Too much, too soon. {pronoun} push {subject} back."),
        ("Gv/Rr", "{pronoun} can't take {subject} in right now. Not today."),
        ("I/A",   "{pronoun} say no. Nothing left to give {subject}."),
        ("V/P",   "Kindly, {pronoun_lower} decline {subject}."),
    ],
    # ── Gv/Rr = You
    "cooperate": [
        ("V/P",   "{pronoun} and I can sort {subject} out together."),
        ("Gv/Rr", "{pronoun} tell me what {pronoun_lower} need, and we handle {subject} together."),
        ("Lv/Er", "I'm with you on {subject}. Whatever {pronoun_lower} need."),
        ("I/A",   "Fine. {pronoun} lead on {subject}, and I follow."),
        ("V/P",   "It's better shared. {pronoun} and I handle {subject} side by side."),
    ],
    # ignore — two distinct cells (see comment in MODE_TEMPLATES):
    # benefit/Lv/Er = attention is elsewhere (I voice)
    "ignore@Lv/Er": [
        ("Lv/Er", "Sorry — what? {pronoun} missed {subject}."),
        ("I/A",   "{pronoun} barely notice {subject} at all."),
        ("Gv/Rr", "{pronoun} have other things to think about than {subject}."),
        ("V/P",   "{pronoun} smile at {subject} and look right past."),
        ("Lv/Er", "Mm. {pronoun} hear {subject}, and {pronoun_lower} think about something else entirely."),
    ],
    # neutral/I/A = no resources or motivation (They voice)
    "ignore@I/A": [
        ("I/A",   "Not now. {pronoun} have nothing left for {subject}."),
        ("I/A",   "{pronoun} let {subject} pass. Nothing left to spend."),
        ("Lv/Er", "{pronoun} can't care about {subject} right now."),
        ("Gv/Rr", "{pronoun} save what's left and skip {subject}."),
        ("V/P",   "{pronoun} would look, if {pronoun_lower} could. {subject_cap} won't register."),
    ],
    # ── neutral ────────────────────────────────────────── (V/P = We)
    "observe": [
        ("V/P",   "{pronoun} watch {subject} for a moment."),
        ("Gv/Rr", "{pronoun} give {subject} a moment and see what happens."),
        ("Lv/Er", "Hm. {subject_cap}... {pronoun} keep looking."),
        ("I/A",   "{pronoun} keep still and watch {subject}."),
        ("V/P",   "Interesting. {pronoun} {mode} {subject} a little closer."),
        ("Gv/Rr", "Nothing to do yet. {pronoun} note {subject} and wait."),
    ],
    # ── Gv/Rr = You
    "group": [
        ("Gv/Rr", "{pronoun}'ve seen {subject} before — just another one of those."),
        ("V/P",   "Nothing new here. {pronoun} put {subject} with the rest."),
        ("I/A",   "Same as always. {pronoun} have seen this a hundred times."),
        ("Lv/Er", "Ha — {subject}. Of course. {pronoun} know this kind."),
        ("Gv/Rr", "{pronoun} don't need to worry about {subject}. It's the usual pattern."),
    ],
    # ── Lv/Er = I
    "formulate": [
        ("Gv/Rr", "Probably nothing — but {pronoun_lower} keep an eye on {subject}."),
        ("Lv/Er", "Hm. {subject_cap}... {pronoun} have a guess about that."),
        ("V/P",   "{pronoun} think {subject} might mean well. Maybe."),
        ("I/A",   "{pronoun} don't know yet. {pronoun} turn {subject} over slowly."),
        ("Gv/Rr", "Let me think. {pronoun} put a guess together about {subject}."),
        ("V/P",   "{subject_cap} could be anything. {pronoun} wonder."),
    ],
    # ── unclassifiable ─────────────────────────────────── (V/P = We)
    "investigate": [
        ("V/P",   "{pronoun} {mode} {subject} — curiosity, not fear."),
        ("Lv/Er", "What is that? {pronoun} move in for a better look at {subject}."),
        ("Gv/Rr", "Careful. {pronoun} {mode} {subject} one step at a time."),
        ("I/A",   "{pronoun} take a look at {subject}, quietly."),
        ("V/P",   "Something's off about {subject}. {pronoun} find out what."),
        ("Lv/Er", "{pronoun} can't leave {subject} alone. {pronoun} need to know."),
    ],
    # ── I/A = They
    "desist": [
        ("I/A",   "Never mind. {pronoun} drop {subject}."),
        ("Lv/Er", "Not worth it. {pronoun} give up on {subject}."),
        ("Gv/Rr", "{pronoun} step back from {subject}. It can wait."),
        ("V/P",   "Some other time. {pronoun} let {subject} go for now."),
        ("I/A",   "{pronoun} stop trying with {subject}."),
    ],
    # ── Gv/Rr = You  (warns the others, not the subject)
    "signal": [
        ("Lv/Er", "Look out! {subject_cap} won't stay away — {pronoun_lower} all need to see this."),
        ("Gv/Rr", "Everyone, listen. {subject_cap} could be trouble, and {pronoun_lower} should know."),
        ("V/P",   "Heads up — watch {subject}. Pass the word."),
        ("I/A",   "{pronoun} should know: {subject}. That's all."),
        ("V/P",   "{pronoun} see {subject}? Tell the others."),
    ],
    # ── Lv/Er = I
    "suppress": [
        ("I/A",   "Steady. Not yet."),
        ("Gv/Rr", "{pronoun} keep still and watch {subject}. Nothing more."),
        ("Lv/Er", "{pronoun} bite it back. {subject_cap} won't get a reaction."),
        ("V/P",   "Breathe. {pronoun} hold it in and wait for {subject} to move."),
        ("Gv/Rr", "Not yet. {pronoun} swallow the urge to react to {subject}."),
    ],
}


def bank_key(mode: str, axis: str = None) -> str:
    """'ignore' is the only word shared by two cells; it is split by axis."""
    if mode == "ignore":
        return "ignore@I/A" if axis == "I/A" else "ignore@Lv/Er"
    return mode


# ── FIT ──────────────────────────────────────────────────────────────
def profile_fit(gains: dict, lean: str) -> float:
    """(mean of the gains of the `lean` axis over the 4 categories - 5) / 5,
    clamped to [-1, 1]. No gains -> 0 (flat profile)."""
    if not gains:
        return 0.0
    short = _SHORT[lean]
    vals = [row.get(short, 5.0) for row in gains.values() if isinstance(row, dict)]
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return max(-1.0, min(1.0, (mean - 5.0) / 5.0))


def state_fit(state: dict, lean: str) -> float:
    """Relative weight of the `lean` axis in the dominant engine's state, minus the
    even split (0.25). Accepts somatic (V,I,Lv,Gv) or mental (P,A,Er,Rr) state."""
    if not state:
        return 0.0
    keymap = _SHORT if "V" in state else _MENTAL
    total = sum(max(state.get(k, 0.0), 0.0) for k in keymap.values())
    if total <= 0:
        return 0.0
    return max(state.get(keymap[lean], 0.0), 0.0) / total - 0.25


def variant_weights(key: str, gains: dict = None, state: dict = None, bank: dict = None) -> list:
    """Weight of each variant of bank[key] (useful for tests and debugging).
    `bank` defaults to BANK (the dialogue bank); pass core.action_bank.ACTION_BANK
    (or any other {key: [(lean, text), ...]} mapping) to weigh a different bank
    with the exact same profile/state logic."""
    bank = BANK if bank is None else bank
    out = []
    for lean, _ in bank[key]:
        w = 1.0 + PROFILE_WEIGHT * profile_fit(gains, lean) + STATE_WEIGHT * state_fit(state, lean)
        out.append(max(MIN_WEIGHT, w))
    return out


def pick_variant(key: str, gains: dict = None, state: dict = None,
                 memory: dict = None, rng=None, bank: dict = None) -> int:
    """Index of the chosen variant: weighted draw, without repeating the
    last one used in this mode (if there is more than one). `bank` picks
    which mapping to draw from (see variant_weights); pass a distinct
    `memory` dict per bank so two banks don't overwrite each other's
    anti-repetition state under the same key."""
    rng = rng or _random
    weights = variant_weights(key, gains, state, bank=bank)
    last = memory.get(key) if memory is not None else None
    if last is not None and len(weights) > 1 and 0 <= last < len(weights):
        weights[last] = 0.0
    idx = rng.choices(range(len(weights)), weights=weights, k=1)[0]
    if memory is not None:
        memory[key] = idx
    return idx


def render_from_bank(raw_mode: str, mode_phrase: str, subject: str, pronoun: str,
                     axis: str = None, gains: dict = None, state: dict = None,
                     memory: dict = None, rng=None):
    """Returns the sentence, or None if the mode is not in the bank (the caller
    then falls back to render_mode_template)."""
    key = bank_key(raw_mode, axis)
    if not USE_RESPONSE_BANK or key not in BANK:
        return None
    idx = pick_variant(key, gains, state, memory, rng)
    template = BANK[key][idx][1]
    subject = subject or "that"
    if subject.lower() == "user":     # the "user" speaker is the one playing: they are addressed as "you"
        subject = "you"
    return template.format(
        subject=subject,
        subject_cap=subject[:1].upper() + subject[1:],
        mode=mode_phrase,
        pronoun=pronoun,
        pronoun_lower=("I" if pronoun == "I" else pronoun.lower()),
    )
