# core/response_matrix.py — UNIQUE HOST
#
# THE 16-CELL RESPONSE MATRIX + SOCIAL POSITIONING AXIS
# ══════════════════════════════════════════════════════════════
# One geometric reading — which single axis dominates the engine's
# current state (Df/Cf) — drives several outputs at once:
#
#   1. RESPONSE_MATRIX[category][axis]   -> base response verb
#   2. SOCIAL_POSITIONING[axis]          -> pronoun / subject / framing
#   3. SENTENCE_TEMPLATES[axis]          -> how to phrase it
#
# "category" (benefit / danger / neutral / unclassifiable) comes from
# the Primary Evaluator scoring the CURRENT input (see
# `primary_evaluator_category` below — still a placeholder heuristic,
# real atomic decomposition/TagsDB scoring pending).
#
# "axis" comes from which single cardinal (N/S/E/O) has the highest
# magnitude in the engine's current state — NOT a 2D quadrant sign
# combination. Same 4 axes for both engines:
#
#   V/P  (north) — somatic Viability  / mental Presence
#   I/A  (south) — somatic Inviability / mental Absence
#   Lv/Er (east) — somatic Local Viability / mental Emotional Resonance
#   Gv/Rr (west) — somatic Global Viability / mental Rational Resonance

# ── 1. THE 16-CELL RESPONSE MATRIX (verbatim from the source material) ──
RESPONSE_MATRIX = {
    "danger":         {"V/P": "attack",     "I/A": "surrender", "Gv/Rr": "protect",   "Lv/Er": "flee"},
    "benefit":        {"V/P": "accept",     "I/A": "deny",      "Gv/Rr": "cooperate", "Lv/Er": "ignore"},
    "neutral":        {"V/P": "observe",    "I/A": "ignore",    "Gv/Rr": "group",     "Lv/Er": "formulate"},
    "unclassifiable": {"V/P": "investigate","I/A": "desist",    "Gv/Rr": "signal",    "Lv/Er": "suppress"},
}

# ── 2. SOCIAL POSITIONING AXIS — pronoun / subject / framing ───────────
# TODO: confirmed as: East=Imposition/I,
# West=Adaptation/You, North=Ecosystem/We, South=World/They-It.
#
# Fix: I/A's pronoun was the literal string "They/It" --
# never actually resolved to one word, so every I/A template rendered
# it verbatim ("They/It won't just stand here"). Resolved to "They":
# plain plural agreement means every verb stays in the base form the
# rest of the system already assumes everywhere else (no separate
# 3rd-person-singular "-s" conjugation path needed just for "It"
# surrenders/denies/etc). Reads as the character speaking about itself
# in the 3rd person -- a dissociation voice under "impersonal limits" --
# which fits I/A's own framing description, but flagging for review
# to confirm that's the intended voice and not literally "they" meaning
# bystanders.
SOCIAL_POSITIONING = {
    "Lv/Er": {"name": "Imposition", "pronoun": "I",         "framing": "asserts itself outward"},
    "Gv/Rr": {"name": "Adaptation", "pronoun": "You",       "framing": "adapts to the listener"},
    "V/P":   {"name": "Ecosystem",  "pronoun": "We",        "framing": "speaks from shared context"},
    "I/A":   {"name": "World",      "pronoun": "They",      "framing": "speaks from impersonal limits"},
}

# ── 3. SENTENCE TEMPLATES PER AXIS ──────────────────────────────────────
# 8 templates per axis (expanded from 3 -- still placeholder
# phrasing, not the final bank, but enough variety that a
# longer conversation doesn't repeat the same 3 shapes every time the
# same axis wins). {pronoun}/{verb}/{focus} fill-in-blank, picked with
# random.choice in build_response/select_axis_response below.
# TODO: replace/extend with the final phrasing
# bank per axis once supplied.
SENTENCE_TEMPLATES = {
    "Lv/Er": [   # Imposition — I
        "{pronoun} {verb} {focus}.",
        "{pronoun} {verb} {focus} right now.",
        "{pronoun} won't just stand here — {pronoun_lower} {verb} {focus}.",
        "There's no hesitation in it -- {pronoun_lower} {verb} {focus}.",
        "{pronoun} {verb} {focus}, plain and simple.",
        "No more waiting. {pronoun} {verb} {focus}.",
        "{pronoun} {verb} {focus} before it's too late.",
        "This ends now -- {pronoun_lower} {verb} {focus}.",
    ],
    "Gv/Rr": [   # Adaptation — You
        "{pronoun} should {verb} {focus}.",
        "Maybe {pronoun_lower} could {verb} {focus}.",
        "{pronoun} might want to {verb} {focus}.",
        "It might help to {verb} {focus}.",
        "Perhaps {pronoun_lower} should {verb} {focus}.",
        "{pronoun} could try to {verb} {focus}, if that works.",
        "Would it help to {verb} {focus}?",
        "{pronoun} think it's worth trying to {verb} {focus}.",
    ],
    "V/P": [     # Ecosystem — We
        "{pronoun} {verb} {focus}.",
        "{pronoun} should {verb} {focus} together.",
        "Given the situation, {pronoun_lower} {verb} {focus}.",
        "Together, {pronoun_lower} {verb} {focus}.",
        "{pronoun} {verb} {focus}, and that feels right.",
        "There's a way through this -- {pronoun_lower} {verb} {focus}.",
        "{pronoun} {verb} {focus}. It's the natural thing to do.",
        "So {pronoun_lower} {verb} {focus}.",
    ],
    "I/A": [     # World — They/It
        "{pronoun} {verb} {focus}.",
        "There are limits — {pronoun_lower} {verb} {focus}.",
        "It cannot be helped: {pronoun_lower} {verb} {focus}.",
        "In the end, {pronoun_lower} {verb} {focus}.",
        "{pronoun} {verb} {focus}. That's just how it is.",
        "Nothing to be done but {verb} {focus}.",
        "{pronoun} {verb} {focus}, whether {pronoun_lower} like it or not.",
        "It comes down to this: {pronoun_lower} {verb} {focus}.",
    ],
}

AXIS_ORDER = ["V/P", "I/A", "Lv/Er", "Gv/Rr"]

# ── VERB PREPOSITIONS — fixes the matrix's 6 non-plain-transitive verbs ──
# Found testing sentence quality end to end: several of the 16
# RESPONSE_MATRIX verbs read as ungrammatical or backwards when a bare
# focus noun is bolted straight on ("I group hero.", "I desist ghost."
# -- desist doesn't even take a direct object in English). The other 9
# (attack/flee/accept/deny/ignore/observe/formulate/investigate/suppress)
# already read fine as plain transitives and are left untouched -- this
# is a targeted fix for the ones that don't, not a rewrite of the verb
# set or its meaning.
VERB_PREPOSITIONS = {
    "surrender": "to",
    "protect":   "against",
    "cooperate": "with",
    "group":     "with",
    "desist":    "from",
    # "signal": "to" REMOVED -- per the paper, signal
    # broadcasts the unclassifiable TO OTHERS/bystanders, not to the
    # thing itself. "signal to {focus}" pointed the preposition at the
    # focus (the unclassifiable stimulus), which is backwards -- the
    # focus is what's being signaled ABOUT, not who's being signaled TO.
    # MODE_TEMPLATES (construction_matcher.py) now writes that direction
    # out explicitly ("signal everyone nearby -- {subject} is close")
    # instead of leaning on an auto-attached preposition that can't
    # express the ABOUT/TO distinction on its own.
}


def verb_phrase(verb: str) -> str:
    """Returns `verb` with its required preposition attached (see
    VERB_PREPOSITIONS), unchanged for the verbs that are already plain
    transitives. Used only for PHRASING -- callers needing the raw mode
    name for matrix/vitality-voice lookups keep using `verb` itself.
    """
    prep = VERB_PREPOSITIONS.get(verb)
    return f"{verb} {prep}" if prep else verb


def dominant_axis(state: dict, keys) -> str:
    """
    Returns which single generic axis (V/P, I/A, Lv/Er, Gv/Rr) has the
    highest magnitude in `state` — NOT a 2D quadrant sign combination.
    `keys` is either SOMATIC_KEYS-style ("V","I","Lv","Gv") or
    MENTAL_KEYS-style ("P","A","Er","Rr").
    """
    is_somatic = "V" in keys
    if is_somatic:
        pairs = {"V/P": state["V"], "I/A": state["I"], "Lv/Er": state["Lv"], "Gv/Rr": state["Gv"]}
    else:
        pairs = {"V/P": state["P"], "I/A": state["A"], "Lv/Er": state["Er"], "Gv/Rr": state["Rr"]}
    return max(pairs, key=pairs.get)


AXIS_TO_CATEGORY = {
    "V/P":   "benefit",          # Viability/Presence — supports continuation
    "I/A":   "danger",           # Inviability/Absence — threatens continuation
    "Gv/Rr": "neutral",          # Global Viability/Rational Resonance — known, organized
    "Lv/Er": "unclassifiable",   # Local Viability/Emotional Resonance — unknown, ambiguous
}
CATEGORY_TO_AXIS = {v: k for k, v in AXIS_TO_CATEGORY.items()}

# ── CATEGORY BIAS — same formula, one level above the axis-gain one ────
# The 16 axis-gain questions (systems/chemical_system.py DEFAULT_GAINS)
# only decide WHICH of the 4 responses wins ONCE a category is already
# selected. They say nothing about how EASILY a given raw stimulus gets
# classified as Danger vs. Benefit vs. Neutral vs. Unclassifiable in the
# first place — that is a separate, one-level-higher question (author,
# ): "pain sensitivity" for instance widens or narrows the
# whole Danger row's threshold, not just one of its 4 cells.
#
# Same mechanic as the axis-gain formula, applied to category selection
# instead of axis-within-category selection:
#
#   final_value(category) = raw_reading(vertex) × (0.5 + bias/10)
#   winning_category = the one with the highest final_value among the 4
#
# DEFAULT_CATEGORY_BIAS (5/10 -> multiplier 1.0 everywhere) reduces to
# plain "raw vertex wins", identical to pre-bias behavior, so a character
# without this set behaves exactly as before.
DEFAULT_CATEGORY_BIAS = {"danger": 5.0, "benefit": 5.0, "neutral": 5.0, "unclassifiable": 5.0}


def primary_evaluator_category_from_axis_push(axis_push: dict, keys=None, category_bias: dict = None) -> str:
    """
    THE REAL PRIMARY EVALUATOR.

    Same geometry as dominant_axis() below — because category and response
    are the same question ("which single vertex dominates?") asked at two
    different moments:

      1. Primary Evaluator (THIS function): dominant_axis() applied to the
         RAW incoming stimulus (`axis_push`, e.g. this cycle's vec_s before
         it blends into the ongoing engine state), FIRST weighted by the
         character's per-category bias (4 questions — see
         DEFAULT_CATEGORY_BIAS above) → whichever vertex wins after that
         weighting names the category via AXIS_TO_CATEGORY.
      2. Response lookup (dominant_axis() called from build_response()):
         the SAME function applied to the CURRENT engine state (Df/Cf,
         after everything integrates this cycle) → that axis, crossed with
         the category from step 1 and weighted by the 16 axis-gain
         questions (systems/chemical_system.py), indexes
         RESPONSE_MATRIX[category][axis] for the actual verb.

    `keys` defaults to somatic (V,I,Lv,Gv); pass mental keys (P,A,Er,Rr) to
    read the mental engine's raw push instead.
    """
    keys = keys or ["V", "I", "Lv", "Gv"]
    bias = category_bias if category_bias is not None else DEFAULT_CATEGORY_BIAS
    is_somatic = "V" in keys

    if is_somatic:
        pairs = {"V/P": axis_push.get("V", 0.0), "I/A": axis_push.get("I", 0.0),
                  "Lv/Er": axis_push.get("Lv", 0.0), "Gv/Rr": axis_push.get("Gv", 0.0)}
    else:
        pairs = {"V/P": axis_push.get("P", 0.0), "I/A": axis_push.get("A", 0.0),
                  "Lv/Er": axis_push.get("Er", 0.0), "Gv/Rr": axis_push.get("Rr", 0.0)}

    finals = {}
    for axis_label, raw in pairs.items():
        category = AXIS_TO_CATEGORY[axis_label]
        finals[axis_label] = raw * (0.5 + bias.get(category, 5.0) / 10.0)

    winning_axis = max(finals, key=finals.get)
    return AXIS_TO_CATEGORY[winning_axis]


def primary_evaluator_category(concept_names: list) -> str:
    """
    LEGACY FALLBACK — kept for when no raw axis vector is available at all
    (e.g. no concepts resolved this cycle, so vec_s is None). Prefer
    primary_evaluator_category_from_axis_push() below, which IS the real
    Primary Evaluator: same dominant-axis geometry as the response lookup,
    just applied to the raw incoming stimulus instead of the current
    engine state.
    """
    from db.db_concepts import CONCEPTS

    danger_tags   = {"adrenaline", "cortisol", "fear", "danger", "flight", "paralysis"}
    benefit_tags  = {"oxytocin", "serotonin", "dopamine", "safe", "trust", "affection"}
    neutral_tags  = {"structure", "known", "identity_anchor"}

    votes = {"benefit": 0, "danger": 0, "neutral": 0, "unclassifiable": 0}

    for name in concept_names:
        node = CONCEPTS.get(name)
        if not node:
            votes["unclassifiable"] += 1
            continue
        related = node.get("related", {})
        found_any = False
        for _, tagset in related.items():
            all_tags = set(tagset.get("somatic", [])) | set(tagset.get("mental", []))
            if all_tags & danger_tags:
                votes["danger"] += 1
                found_any = True
            if all_tags & benefit_tags:
                votes["benefit"] += 1
                found_any = True
            if all_tags & neutral_tags:
                votes["neutral"] += 1
                found_any = True
        if not found_any:
            votes["unclassifiable"] += 1

    return max(votes, key=votes.get)


def build_response(dominant_engine_state: dict, dominant_engine_keys, concept_names: list, focus: str = "that") -> dict:
    """
    LEGACY — kept only as a reference for the template-fill mechanics
    (SENTENCE_TEMPLATES.format(...)), which select_axis_response() below
    reuses. Not called anywhere in the real cycle (cycle_manager_v5.py
    calls select_axis_response() instead — see 2026-09-03 session).
    """
    axis = dominant_axis(dominant_engine_state, dominant_engine_keys)
    category = primary_evaluator_category(concept_names)

    verb = RESPONSE_MATRIX[category][axis]
    positioning = SOCIAL_POSITIONING[axis]
    pronoun = positioning["pronoun"]

    import random
    template = random.choice(SENTENCE_TEMPLATES[axis])
    # "I" never lowercases in English, even mid-sentence.
    pronoun_lower = "I" if pronoun == "I" else pronoun.lower()
    sentence = template.format(pronoun=pronoun, pronoun_lower=pronoun_lower,
                                verb=verb_phrase(verb), focus=focus)

    return {
        "axis": axis,
        "category": category,
        "verb": verb,
        "pronoun": pronoun,
        "social_positioning": positioning["name"],
        "sentence": sentence,
    }


def select_axis_response(axis: str, category: str, character_name: str = None,
                          raw_text: str = "", forced_focus: str = None,
                          profile_gains: dict = None, engine_state: dict = None,
                          variant_memory: dict = None, rng=None,
                          extra_known_names=None) -> dict:
    """
    THE REAL RESPONSE BUILDER — replaces output/phrase_builder.py
    (quadrant/tension FORMATS) as of the 2026-09-03 session. Called from
    motors/cycle_manager_v5.py:_build_output() with the axis of whichever
    engine (somatic/mental) dominates this cycle, and the category
    already computed by primary_evaluator_category_from_axis_push().

    Pipeline: RESPONSE_MATRIX[category][axis] -> mode/verb. Then
    core/construction_matcher.py parses `raw_text` (spaCy), extracts the
    grammatical subject (character-name-normalized — fixes the "name
    read as apposition of the danger noun" mis-parse found this
    session), and matches whichever of the 30 constructions it has
    patterns for so far.

    "investigate" (the only mode reached by North's two interrogative
    constructions, #28/#29 — see the 2026-09-03 system-state notes §33
    "why only North asks") uses the pronoun-reflection question
    generators instead of the flat SENTENCE_TEMPLATES fill: genuine
    curiosity (make_what_question) is tried first, falling back to the
    confrontational form (make_why_question) only if there's no direct
    object to turn into "what" (see construction_matcher.py §4 for why
    these are two different transformations, not one).

    HONEST STATE (audited 2026-09-08, corrects a stale note from the
    2026-09-03 session that said "5 of 29"): construction_matcher.py
    actually detects 27 of 29 labels correctly when tested against
    proper example sentences for each (25/29 on a first pass turned out
    to include 2 bad test sentences, not code gaps -- see
    core/construction_matcher.py's REORDERED fix and the METALINGUISTIC
    comma-splice note). The 2 real remaining gaps: METALINGUISTIC
    misparses on informal comma-splices ("What I mean is, X" -- spaCy's
    small model attaches "is" as parataxis instead of ROOT; works fine
    without the comma splice), and construction coverage generally still
    doesn't guarantee a match for every input -- when nothing matches,
    this still returns a sentence via the same SENTENCE_TEMPLATES fill
    build_response() used, so the cycle never breaks.

    forced_focus (2026-09-09, speaker selector): when the caller already
    knows WHO is being reacted to (a narrator scene sentence still gets
    parsed as before, but any other speaker -- "user", "bandit", a
    proper name -- means the identity is already settled), this
    overrides the parsed `subject` after construction-matching still
    runs on `raw_text` (so grammar/construction detection of WHAT was
    said is unaffected -- only WHO it's about is pinned).

    CHANGED 2026-09-10 (16-mode construction audit): the middle step
    used to be best_construction_for_axis()+render_construction(), which
    picked a construction by AXIS only -- never checked that the
    construction's assigned mode(s) actually matched the verb that won
    THIS cycle, so a `deny` cycle could render a construction written
    for `investigate`, etc (see construction_matcher.py's MODE_TEMPLATES
    comment for the concrete tone breaks this caused). Replaced with
    render_mode_template(), keyed directly by the winning verb -- no
    axis-only mismatch is possible anymore. `analyze_input()`'s grammar-
    construction detection (`constructions_matched`) is still run and
    still returned for diagnostics/future use, just no longer used to
    pick the OUTPUT phrase.
    """
    from core.construction_matcher import (
        analyze_input, make_what_question, make_why_question,
        render_mode_template,
    )

    verb = RESPONSE_MATRIX[category][axis]
    positioning = SOCIAL_POSITIONING[axis]
    pronoun = positioning["pronoun"]

    # known_names (found alongside the action-bank subject-mismatch
    # report; see extract_subject()'s docstring in construction_matcher.py):
    # the proper names already known to be real THIS turn -- the
    # reacting character, whoever is being addressed, and (via
    # extra_known_names, set by the caller to {user_name} -- see
    # cycle_manager_v5.py) the player's own name, since a NARRATOR
    # scene line can reference the player by name too ("the bandit
    # attacks joaquin") without forced_focus being set at all (narrator
    # turns don't pin a focus) -- so a name typed in lowercase in the
    # raw text is still recognized as a name (no "the", correct
    # capitalization) instead of being read as a common noun.
    known_names = {n.lower(): n for n in (character_name, forced_focus, *(extra_known_names or ())) if n}
    parsed = analyze_input(raw_text, character_name, known_names) if raw_text else {"subject": None, "constructions": []}
    subject = forced_focus or parsed["subject"] or "that"

    sentence = None
    # Fix: make_what_question/make_why_question
    # work by REFLECTING the sentence's own subject (swapping "you" ->
    # "I", see _PRONOUN_REFLECT) -- that premise only holds when someone
    # is actually addressing Delia directly ("you shouldn't do that!" ->
    # "Why shouldn't I do that?"). Fed a third-person narrator scene
    # line instead ("the bandit falls, defeated"), there's no pronoun to
    # reflect, nsubj is just a random noun, and the result is a
    # malformed question ("Why bandit falls the defeated?"), not a
    # relevant reflection of anything. `forced_focus` (set by the
    #  speaker selector for any speaker other than "narrator") is
    # exactly the signal for "this turn addressed Delia directly" --
    # gating on it here keeps the reflective questions for genuine
    # address and falls back to the normal subject+verb template
    # (already correct -- "We investigate the bandit.") for narrator
    # scene description instead of forcing a broken reflection.
    if verb == "investigate" and raw_text and forced_focus is not None:
        sentence = make_what_question(raw_text) or make_why_question(raw_text)

    # bank of 5-6 variants per mode with profile-based selection
    # (core/response_bank.py). profile_gains = gains of the dominant engine,
    # engine_state = its current state, variant_memory = per-session dict so the
    # last variant is not repeated. All optional: without them the bank
    # draws evenly (with anti-repetition if there is memory). render_mode_template
    # remains as the fallback.
    if not sentence:
        from core.response_bank import render_from_bank
        sentence = render_from_bank(verb, verb_phrase(verb), subject, pronoun, axis=axis,
                                     gains=profile_gains, state=engine_state,
                                     memory=variant_memory, rng=rng)

    if not sentence:
        sentence = render_mode_template(verb, verb_phrase(verb), subject, pronoun, axis=axis)

    if not sentence:
        import random
        template = random.choice(SENTENCE_TEMPLATES[axis])
        pronoun_lower = "I" if pronoun == "I" else pronoun.lower()
        sentence = template.format(pronoun=pronoun, pronoun_lower=pronoun_lower,
                                    verb=verb_phrase(verb), focus=subject)

    return {
        "axis": axis,
        "category": category,
        "verb": verb,
        "pronoun": pronoun,
        "social_positioning": positioning["name"],
        "subject": subject,
        "constructions_matched": parsed["constructions"],
        "sentence": sentence,
    }
