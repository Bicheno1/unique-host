# core/action_bank.py — UNIQUE HOST
#
# PER-MODE ACTION-LINE BANK (the <<...>> gesture, not the spoken line)
# ══════════════════════════════════════════════════════════════
# Same problem as core/response_bank.py, one layer down. Before this
# file existed, motors/cycle_manager_v5.py built the <<...>> fragment
# by gerund-inflecting the winning mode's verb directly (lemminflect,
# tag=VBG) and nothing else: "suppress" -> always "suppressing
# {subject}", "accept" -> always "accepting {subject}". Grammatically
# fine, but flat over a whole session — no synonyms, no common human
# gestures (a nod, a smile, a "thanks"), no variety at all for a mode
# that fires often (e.g. "suppress" during a drawn-out threat scene).
#
# HOW IT WORKS (identical machinery to response_bank.py — see that
# file's header for the full explanation of `lean`, profile_fit,
# state_fit and the weighted anti-repetition draw; this file only adds
# the DATA, reusing core.response_bank.pick_variant with bank=ACTION_BANK)
#   1. The mode was already decided by the matrix. This does not touch it.
#   2. Each mode has 5-6 gerund-phrase variants, all describing the SAME
#      underlying action, just as a different concrete gesture/synonym:
#      "accept" ranges from the literal "accepting {subject}" to
#      "thanking {subject}", "nodding to {subject}", "smiling at {subject}".
#      "attack" ranges from "attacking {subject}" to "tearing into
#      {subject}", "slaying {subject}", "striking {subject} down".
#   3. Each variant carries a `lean` tag (same 4 axes as response_bank.py)
#      so the SAME personality/state weighting used for the dialogue line
#      also nudges which gesture shows up — a composed (Gv/Rr) character
#      leans toward "studying {subject}" over "eyeing {subject}" for
#      `observe`, for instance.
#   4. Selection/weighting is delegated entirely to
#      core.response_bank.pick_variant(key, gains, state, memory, rng,
#      bank=ACTION_BANK) — a SEPARATE memory dict from the dialogue bank's
#      (see motors/cycle_manager_v5.py: self._action_variant_memory vs
#      self._variant_memory) so the two banks don't fight over the same
#      per-mode "last variant used" slot.
#
# WRITING RULES
#   * Templates use only {subject} (and, for parity with response_bank.py,
#     {subject_cap} — available but rarely needed since action lines read
#     lowercase, e.g. "<<attacking the bandit>>").
#   * No pronoun slot: action lines are always third-person/gerund
#     descriptions of what's happening, never "I"/"we"/"you" narration.
#   * A variant MAY omit {subject} entirely when the gesture is
#     self-contained ("holding still", "giving up", "dropping it") —
#     str.format() ignores unused kwargs, so this is safe.
#   * subject can be "the bandit", "Mark", "that" or "you" (already
#     resolved by the caller — see cycle_manager_v5.py's
#     _action_subject); avoid a 3rd-person verb directly on {subject}
#     for the same reason response_bank.py avoids it ("You is" would break).
#
# To edit: add/remove (lean, text) tuples in ACTION_BANK.
# tests/test_action_bank.py validates format, coverage and variety,
# mirroring tests/test_response_bank.py.

USE_ACTION_BANK = True   # False -> caller falls back to the old plain gerund

# ── THE BANK ────────────────────────────────────────────────────────────
ACTION_BANK = {
    # ── danger ─────────────────────────────────────────────────────
    "attack": [
        ("Lv/Er", "tearing into {subject}"),
        ("V/P",   "attacking {subject}"),
        ("Gv/Rr", "closing in on {subject}"),
        ("I/A",   "striking {subject} down"),
        ("Lv/Er", "slaying {subject}"),
        ("V/P",   "driving hard at {subject}"),
        ("Lv/Er", "lunging at {subject}"),
        ("V/P",   "charging at {subject}"),
        ("I/A",   "cutting {subject} down"),
        ("Gv/Rr", "going for {subject}"),
    ],
    "surrender": [
        ("I/A",   "giving up"),
        ("Lv/Er", "backing down from {subject}"),
        ("Gv/Rr", "yielding to {subject}"),
        ("V/P",   "lowering everything"),
        ("I/A",   "surrendering to {subject}"),
        ("Lv/Er", "raising both hands"),
        ("I/A",   "going still under {subject}"),
        ("Gv/Rr", "letting {subject} win"),
        ("V/P",   "dropping the fight"),
    ],
    "protect": [
        ("Gv/Rr", "standing guard against {subject}"),
        ("V/P",   "shielding the others from {subject}"),
        ("I/A",   "holding the line against {subject}"),
        ("Lv/Er", "stepping between {subject} and the others"),
        ("Gv/Rr", "protecting against {subject}"),
        ("V/P",   "putting the body between {subject} and the others"),
        ("Gv/Rr", "warding off {subject}"),
        ("I/A",   "keeping {subject} at bay"),
        ("Lv/Er", "guarding against {subject}"),
    ],
    "flee": [
        ("Lv/Er", "bolting from {subject}"),
        ("I/A",   "fleeing {subject}"),
        ("Gv/Rr", "pulling back from {subject}"),
        ("V/P",   "getting clear of {subject}"),
        ("Lv/Er", "running from {subject}"),
        ("Lv/Er", "sprinting away from {subject}"),
        ("I/A",   "scrambling clear of {subject}"),
        ("Gv/Rr", "making a break from {subject}"),
        ("V/P",   "ducking away from {subject}"),
    ],
    # ── benefit ────────────────────────────────────────────────────
    "accept": [
        ("V/P",   "welcoming {subject}"),
        ("Gv/Rr", "nodding to {subject}"),
        ("Lv/Er", "smiling at {subject}"),
        ("I/A",   "accepting {subject}"),
        ("V/P",   "thanking {subject}"),
        ("Lv/Er", "beaming at {subject}"),
        ("V/P",   "embracing {subject}"),
        ("Gv/Rr", "shaking hands with {subject}"),
        ("V/P",   "opening up to {subject}"),
    ],
    "deny": [
        ("I/A",   "turning {subject} away"),
        ("Lv/Er", "pushing {subject} back"),
        ("Gv/Rr", "declining {subject}"),
        ("I/A",   "denying {subject}"),
        ("V/P",   "shaking off {subject}"),
        ("I/A",   "refusing {subject}"),
        ("Gv/Rr", "holding a hand up to {subject}"),
        ("Lv/Er", "closing off to {subject}"),
    ],
    "cooperate": [
        ("V/P",   "working with {subject}"),
        ("Gv/Rr", "cooperating with {subject}"),
        ("Lv/Er", "teaming up with {subject}"),
        ("I/A",   "falling in step with {subject}"),
        ("V/P",   "joining {subject}"),
        ("Lv/Er", "shaking on it with {subject}"),
        ("Gv/Rr", "syncing up with {subject}"),
        ("V/P",   "pitching in with {subject}"),
        ("Gv/Rr", "linking up with {subject}"),
    ],
    # ignore — two distinct cells (see bank_key in response_bank.py):
    "ignore@Lv/Er": [
        ("Lv/Er", "missing {subject} entirely"),
        ("V/P",   "smiling past {subject}"),
        ("Gv/Rr", "looking past {subject}"),
        ("I/A",   "barely noticing {subject}"),
        ("Lv/Er", "drifting off from {subject}"),
        ("Lv/Er", "tuning {subject} out"),
        ("Gv/Rr", "letting the mind wander from {subject}"),
        ("V/P",   "glancing past {subject}"),
    ],
    "ignore@I/A": [
        ("I/A",   "letting {subject} pass"),
        ("Lv/Er", "waving {subject} off"),
        ("Gv/Rr", "skipping past {subject}"),
        ("V/P",   "passing on {subject}"),
        ("I/A",   "ignoring {subject}"),
        ("I/A",   "brushing {subject} aside"),
        ("V/P",   "sparing nothing for {subject}"),
        ("Gv/Rr", "moving on from {subject}"),
    ],
    # ── neutral ────────────────────────────────────────────────────
    "observe": [
        ("V/P",   "watching {subject}"),
        ("Gv/Rr", "studying {subject}"),
        ("Lv/Er", "eyeing {subject}"),
        ("I/A",   "keeping still, watching {subject}"),
        ("V/P",   "observing {subject}"),
        ("V/P",   "taking in {subject}"),
        ("Gv/Rr", "tracking {subject}"),
        ("Lv/Er", "sizing up {subject}"),
    ],
    "group": [
        ("Gv/Rr", "filing {subject} away as familiar"),
        ("V/P",   "shrugging off {subject} as nothing new"),
        ("I/A",   "recognizing {subject} for what it is"),
        ("Lv/Er", "grouping {subject} with the rest"),
        ("Gv/Rr", "sorting {subject} into the usual pattern"),
        ("Gv/Rr", "tagging {subject} as known"),
        ("V/P",   "slotting {subject} into place"),
        ("I/A",   "waving {subject} off as ordinary"),
    ],
    "formulate": [
        ("Gv/Rr", "puzzling over {subject}"),
        ("Lv/Er", "guessing at {subject}"),
        ("V/P",   "turning {subject} over"),
        ("I/A",   "mulling over {subject}"),
        ("Gv/Rr", "formulating a guess about {subject}"),
        ("Gv/Rr", "working out a theory about {subject}"),
        ("Lv/Er", "chewing on {subject}"),
        ("V/P",   "sketching out an idea about {subject}"),
    ],
    # ── unclassifiable ─────────────────────────────────────────────
    "investigate": [
        ("V/P",   "investigating {subject}"),
        ("Lv/Er", "leaning in for a better look at {subject}"),
        ("Gv/Rr", "approaching {subject} carefully"),
        ("I/A",   "taking a quiet look at {subject}"),
        ("V/P",   "poking at {subject}"),
        ("Lv/Er", "circling {subject}"),
        ("V/P",   "reaching toward {subject}"),
        ("Gv/Rr", "drawing closer to {subject}"),
    ],
    "desist": [
        ("I/A",   "dropping it"),
        ("Lv/Er", "giving up on {subject}"),
        ("Gv/Rr", "stepping back from {subject}"),
        ("V/P",   "letting {subject} go"),
        ("I/A",   "desisting from {subject}"),
        ("I/A",   "waving it off"),
        ("Lv/Er", "calling it quits on {subject}"),
        ("Gv/Rr", "leaving {subject} be"),
    ],
    "signal": [
        ("Lv/Er", "shouting a warning about {subject}"),
        ("Gv/Rr", "signaling to the others about {subject}"),
        ("V/P",   "pointing out {subject}"),
        ("I/A",   "flagging {subject}"),
        ("V/P",   "waving the others toward {subject}"),
        ("Lv/Er", "raising the alarm about {subject}"),
        ("Gv/Rr", "calling out about {subject}"),
        ("V/P",   "alerting everyone to {subject}"),
    ],
    "suppress": [
        ("I/A",   "holding still"),
        ("Gv/Rr", "watching {subject} without a word"),
        ("Lv/Er", "biting it back"),
        ("V/P",   "holding it in"),
        ("Gv/Rr", "swallowing the urge to react to {subject}"),
        ("Lv/Er", "keeping a straight face"),
        ("I/A",   "grinding it down"),
        ("Lv/Er", "locking the jaw"),
        ("V/P",   "forcing calm"),
        ("I/A",   "staying rigid"),
    ],
}


def render_action_from_bank(raw_mode: str, subject: str, axis: str = None,
                             gains: dict = None, state: dict = None,
                             memory: dict = None, rng=None):
    """Returns the gesture line, or None if the mode is not in the bank
    (the caller then falls back to the old plain-gerund construction)."""
    from core.response_bank import bank_key, pick_variant

    key = bank_key(raw_mode, axis)
    if not USE_ACTION_BANK or key not in ACTION_BANK:
        return None
    idx = pick_variant(key, gains, state, memory, rng, bank=ACTION_BANK)
    template = ACTION_BANK[key][idx][1]
    subject = subject or "that"
    return template.format(subject=subject, subject_cap=subject[:1].upper() + subject[1:])
