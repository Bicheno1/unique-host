# core/construction_matcher.py — UNIQUE HOST
#
# BRIDGE BETWEEN THE MARKER PARSER AND THE 16-CELL RESPONSE MATRIX,
# built with spaCy. Closes work from the session:
#
#   1. Subject extraction from raw fragmented roleplay input (character-
#      name normalization solves the "Cecilia read as apposition of the
#      danger noun" mis-parse observed).
#   2. A real DependencyMatcher for a first batch of the 30 grammatical
#      constructions (CCM constructions-by-axis document), each construction
#      mapped to its (axis, category, mode) cell in RESPONSE_MATRIX.
#   3. Pronoun-reflection question generators (why/what) for when the
#      winning mode is a question-type mode (Observe/Investigate, the
#      only two cells with an interrogative construction assigned).
#
# HONEST STATE: this covers the constructions actually validated against
# spaCy (5 of North's 9 fully pattern-matched; the rest of
# the 30 are listed in CONSTRUCTION_MODE_MAP with their mode already
# known from the docx, but without a DependencyMatcher pattern yet — see
# "PENDING PATTERNS" below). Nothing here is simulated; every pattern
# below was tested against sentences NOT taken from the docx.

import re

_nlp = None
_matcher = None


def get_nlp():
    """Lazy-load spaCy — avoids the import/model-load cost when this
    module is imported but construction matching isn't used this cycle."""
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# ── 1. CONSTRUCTION -> (axis, category, mode) MAP ──────────────────────
# Verbatim from the CCM constructions-by-axis document, reorganized by the 16
# RESPONSE_MATRIX cells ( — this IS
# that table, as code). Keyed by the EXACT label resolve_constructions
# returns (not by docx number) so callers can cross-reference a match
# directly, with no name-normalization step to get wrong. "*" (two
# modes) constructions: the grammar fixes the axis; the real category
# from primary_evaluator_category_from_axis_push picks which of the
# two wins at runtime — modes[0] is used if the caller doesn't
# disambiguate further.
CONSTRUCTION_MODE_MAP = {
    # LABEL: (docx num, axis, modes)   axis uses response_matrix.py's own keys
    "OPINION":                  (4,  "V/P",   ["accept"]),
    "CONDITIONAL":              (8,  "V/P",   ["attack"]),
    "SUBORDINATION":            (13, "V/P",   ["observe"]),
    "HYPOTHETICAL":             (14, "V/P",   ["investigate"]),
    "NUANCE":                   (16, "V/P",   ["accept"]),
    "PURPOSE":                  (18, "V/P",   ["attack"]),
    "MANNER":                   (22, "V/P",   ["investigate"]),
    "DIRECT_Q":                 (28, "V/P",   ["observe"]),
    "INDIRECT_Q":               (29, "V/P",   ["investigate"]),

    "SIMPLE_CONNECTOR":         (5,  "Gv/Rr", ["cooperate"]),
    "CAUSAL":                   (7,  "Gv/Rr", ["protect"]),
    "CONCESSIVE":               (9,  "Gv/Rr", ["cooperate"]),
    "TEMPORAL":                 (10, "Gv/Rr", ["signal"]),
    "EXPLANATORY":              (11, "Gv/Rr", ["signal"]),
    "REORDERED":                (12, "Gv/Rr", ["group"]),
    "COMPARATIVE":              (19, "Gv/Rr", ["group"]),
    "RESTRICTIVE_RELATIVE":     (23, "Gv/Rr", ["protect"]),
    "NON_RESTRICTIVE_RELATIVE": (24, "Gv/Rr", ["cooperate"]),
    "IMPERATIVE":               (26, "Gv/Rr", ["protect", "signal"]),

    "EXISTENTIAL":              (1,  "Lv/Er", ["flee"]),
    "EXPERIENTIAL":             (2,  "Lv/Er", ["flee", "formulate"]),
    "EVALUATIVE":               (3,  "Lv/Er", ["ignore", "suppress"]),
    "SUPERLATIVE":              (20, "Lv/Er", ["ignore"]),
    "EXCLAMATIVE":              (27, "Lv/Er", ["suppress"]),

    "NEGATION":                 (6,  "I/A",   ["deny", "desist"]),
    "METALINGUISTIC":           (15, "I/A",   ["ignore"]),
    "RESULT":                   (21, "I/A",   ["surrender"]),
    "PASSIVE_VOICE":            (25, "I/A",   ["surrender", "ignore"]),
    "DISCOURSE_CONNECTOR":      (30, "I/A",   ["deny", "desist"]),
    # 17 -- missing from the source doc, not written yet
}


# ── 1b. PHRASE TEMPLATES — one per construction, real output at last ───
# Each fills {subject} (from extract_subject), {mode} (the verb from
# RESPONSE_MATRIX[category][axis] -- attack/accept/deny/etc, all plain
# base-form verbs so they drop into 1st person present cleanly),
# {pronoun}/{pronoun_lower} (from SOCIAL_POSITIONING[axis]). Loosely
# follows each construction's own "Predicate" shape from the docx —
# not a transcription of the docx's specific example, a reusable frame
# for whatever subject/mode land this cycle.
PHRASE_TEMPLATES = {
    "CONDITIONAL":              "If {subject} gets closer, {pronoun_lower} {mode} it.",
    "HYPOTHETICAL":             "If {subject} had moved, {pronoun_lower} would have had to {mode} it.",
    "MANNER":                   "{pronoun} {mode} {subject} as if there were no other way.",
    "PURPOSE":                  "{pronoun} {mode} {subject} so that this ends.",
    "OPINION":                  "{pronoun} think {pronoun_lower} should {mode} {subject}.",
    "SUBORDINATION":            "What {subject} did doesn't change that {pronoun_lower} {mode} it.",
    "NUANCE":                   "In a way, {pronoun_lower} {mode} {subject}.",
    "SIMPLE_CONNECTOR":         "{pronoun} see {subject} and {pronoun_lower} {mode} it.",
    "CAUSAL":                   "{pronoun} {mode} {subject} because there's no other option.",
    "CONCESSIVE":               "Although it's risky, {pronoun_lower} {mode} {subject}.",
    "TEMPORAL":                 "When {subject} moves, {pronoun_lower} {mode} it.",
    "EXPLANATORY":              "The thing is, {pronoun_lower} {mode} {subject}.",
    "REORDERED":                "Right there, {pronoun_lower} {mode} {subject}.",
    "COMPARATIVE":              "{subject} matters more than anything else, so {pronoun_lower} {mode} it.",
    "RESTRICTIVE_RELATIVE":     "The {subject} causing this is what {pronoun_lower} {mode}.",
    "NON_RESTRICTIVE_RELATIVE": "{subject}, which changes everything, is what {pronoun_lower} {mode}.",
    "IMPERATIVE":               "{mode_cap} {subject}.",
    "EXISTENTIAL":              "There's no way around it -- {pronoun_lower} {mode} {subject}.",
    "EXPERIENTIAL":             "{pronoun} sense {subject} and {pronoun_lower} {mode} it.",
    "EVALUATIVE":               "{subject} matters, so {pronoun_lower} {mode} it.",
    "SUPERLATIVE":              "{subject} is the worst of it, so {pronoun_lower} {mode} it.",
    "EXCLAMATIVE":              "What a mess -- {pronoun_lower} {mode} {subject}!",
    "NEGATION":                 "{pronoun} won't just stand here -- {pronoun_lower} {mode} {subject}.",
    "METALINGUISTIC":           "What {pronoun_lower} mean is, {pronoun_lower} {mode} {subject}.",
    "RESULT":                   "It's so bad that {pronoun_lower} {mode} {subject}.",
    "PASSIVE_VOICE":            "{subject} was left behind, so {pronoun_lower} {mode} it.",
    "DISCOURSE_CONNECTOR":      "However it looks, {pronoun_lower} {mode} {subject}.",
    "DIRECT_Q":                 "Should {pronoun_lower} {mode} {subject}?",
    "INDIRECT_Q":               "{pronoun} wonder whether {pronoun_lower} should {mode} {subject}.",
}


# ── 1c. MODE_TEMPLATES — response-function-first bank ─────
# REPLACES the old axis-only construction selection for OUTPUT PHRASING.
# CONSTRUCTION_MODE_MAP/PHRASE_TEMPLATES above were organized by GRAMMAR
# TYPE (conditional, passive, comparative...) inherited straight from
# the docx, with no check that a matched construction's grammar-frame
# tone actually fit the MODE that ended up winning the cycle -- see
# best_construction_for_axis, which only compared axis, never mode.
# Two concrete failures this caused, found auditing all 16 modes against
# their real definitions (paper): NEGATION's frame ("won't just
# stand here") is active/defiant, used for both `deny` (should read as
# saturation/can't-process-more) and `desist` (should read as
# withdrawal) -- for `desist` specifically the frame is self-
# contradictory ("won't stand here" + "desist" cancel each other).
# EVALUATIVE/SUPERLATIVE for `ignore` (Lv/Er) frame the focus as
# mattering/being "the worst" when the paper defines that `ignore` as
# attention being elsewhere -- the focus not registering at all, not
# being judged and dismissed.
#
# Keyed by MODE (the actual RESPONSE_MATRIX verb), not by grammar label,
# so there is no axis-only mismatch possible anymore: the template bank
# for the winning verb IS the winning verb's bank. Grounded in how each
# reaction actually reads in text-roleplay convention for that verb's
# real definition (paper), not in a borrowed grammar-type frame.
# 2 variants per mode for the same anti-repetition reason SENTENCE_
# TEMPLATES has 8 per axis; kept smaller here since these are far more
# specific than the flat per-axis fallback.
#
# PRONOUN NOTE: I/A's SOCIAL_POSITIONING pronoun was "They/It" (a
# literal placeholder never resolved -- would render "They/It surrender
# to X" verbatim). Resolved here to "They" (see SOCIAL_POSITIONING fix
# below): plural agreement lets every verb stay in the base form the
# rest of the system already assumes (no "it surrenders/它denies"
# 3rd-person-singular -s conjugation logic needed anywhere). Open
# question: "They" reads as the character talking about
# itself in the 3rd person (dissociation under I/A's "impersonal
# limits" framing) -- confirm that's the intended voice, not literally
# "they" meaning bystanders.
MODE_TEMPLATES = {
    # ── danger ──
    "attack":     ["{pronoun} {mode} {subject} without hesitation.",
                   "{pronoun} {mode} {subject} head-on -- no room for anything else."],
    "surrender":  ["There's no fighting it anymore -- {pronoun_lower} {mode} {subject}.",
                   "{pronoun} go still -- {pronoun_lower} {mode} {subject}."],
    "protect":    ["{pronoun} {mode} {subject}, standing between it and everyone else.",
                   "Not while {pronoun_lower} stand here -- {pronoun_lower} {mode} {subject}."],
    "flee":       ["There's no time -- {pronoun_lower} {mode} {subject}.",
                   "{pronoun} {mode} {subject} before it's too late."],
    # ── benefit ──
    "accept":     ["{pronoun} {mode} {subject}, no hesitation.",
                   "{pronoun} {mode} {subject} -- {pronoun_lower} can handle it."],
    "deny":       ["{pronoun} {mode} {subject} -- there's no room left for it.",
                   "Nothing left to give -- {pronoun_lower} {mode} {subject}."],
    "cooperate":  ["Here -- {pronoun_lower} {mode} {subject}.",
                   "{pronoun} {mode} {subject}. It's better shared."],
    # NOTE: "ignore" appears in TWO cells (benefit/Lv/Er and neutral/I/A)
    # with genuinely different flavors per the paper (Lv/Er = attention
    # elsewhere; I/A = lacks resources/motivation) -- can't share one
    # entry here the way the old system tried to. Lv/Er's goes under
    # its own key below (post-lookup disambiguated by axis, see
    # render_mode_template); this key is a safe generic fallback if
    # a caller ever asks for "ignore" without axis context.
    "ignore":     ["{pronoun} {mode} {subject} -- {pronoun_lower}'m already looking elsewhere.",
                   "{subject_cap} doesn't register -- {pronoun_lower}'m somewhere else entirely."],
    # ── neutral ──
    "observe":    ["{pronoun} {mode} {subject}, taking it in.",
                   "{pronoun} {mode} {subject} closer, watching how it moves."],
    "group":      ["{pronoun} {mode} {subject} -- just another one of those.",
                   "Just another one of those -- {pronoun_lower} {mode} {subject}."],
    "formulate":  ["{pronoun} {mode} a quick guess about {subject}.",
                   "Probably nothing -- but {pronoun_lower} {mode} it anyway."],
    # ── unclassifiable ──
    "investigate":["{pronoun} {mode} {subject} -- curiosity, not fear.",
                   "{pronoun} {mode} {subject}, moving closer to get a better look."],
    "desist":     ["{pronoun} {mode} {subject} -- not now, not like this.",
                   "{pronoun}'re not going to think about {subject} right now -- {pronoun_lower} {mode} it."],
    # "signal" drops its old "to {subject}" preposition on purpose: the
    # paper defines signal as broadcasting the unclassifiable TO OTHERS,
    # not addressing the unclassifiable thing itself -- verb_phrase()
    # used to attach "to" pointing straight at the focus, the wrong
    # target. See VERB_PREPOSITIONS below (entry removed).
    "signal":     ["\"Look out!\" -- {pronoun_lower} {mode} everyone nearby. {subject_cap} is close.",
                   "{pronoun} {mode} the others -- {subject} is close."],
    "suppress":   ["{pronoun} go still, watching {subject} without moving.",
                   "{pronoun} {mode} the urge to react -- not yet."],
}

# The Lv/Er flavor of "ignore" (attention elsewhere, benefit) needs its
# own bank distinct from the I/A flavor (depletion, neutral) above --
# keyed separately since MODE_TEMPLATES is keyed by verb string alone
# and "ignore" the string is shared by both cells.
_IGNORE_LV_ER = ["{pronoun} {mode} {subject} -- {pronoun_lower}'m already looking elsewhere.",
                 "{subject_cap} doesn't register -- {pronoun_lower}'m somewhere else entirely."]
_IGNORE_I_A = ["{pronoun} {mode} {subject} -- nothing left for it.",
               "Not now -- {pronoun_lower} {mode} {subject}, there's nothing left to give."]


def render_mode_template(raw_mode: str, mode_phrase: str, subject: str, pronoun: str, axis: str = None) -> str | None:
    """
    Response-function-first phrasing: picks straight from MODE_TEMPLATES
    by the WINNING verb (never mismatches mode/tone the way
    best_construction_for_axis()+render_construction() could -- see the
    comment above MODE_TEMPLATES).

    `raw_mode` is the bare RESPONSE_MATRIX verb (used as the dict key
    and for `axis` disambiguation below); `mode_phrase` is that verb
    WITH its preposition already attached by response_matrix.verb_phrase()
    (e.g. "protect against", "desist from") -- same split
    render_construction() used, needed because "protect {subject}"
    reads backwards (would mean protecting the danger itself, not
    protecting against it) for protect/cooperate/group/desist/surrender.
    `signal` is the one exception: it now carries NO preposition (see
    VERB_PREPOSITIONS in response_matrix.py) because its old "to
    {subject}" pointed at the threat instead of at the bystanders who
    are the real target of a signal/alarm -- MODE_TEMPLATES writes that
    direction out explicitly instead ("signal everyone nearby").

    `axis` disambiguates "ignore"'s two different real flavors (Lv/Er
    vs I/A, see _IGNORE_LV_ER/_IGNORE_I_A) -- omit axis to get the
    generic MODE_TEMPLATES["ignore"].
    """
    import random
    if raw_mode == "ignore" and axis == "Lv/Er":
        bank = _IGNORE_LV_ER
    elif raw_mode == "ignore" and axis == "I/A":
        bank = _IGNORE_I_A
    else:
        bank = MODE_TEMPLATES.get(raw_mode)
    if not bank:
        return None
    template = random.choice(bank)
    subject = subject or "that"
    pronoun_lower = "I" if pronoun == "I" else pronoun.lower()
    return template.format(
        subject=subject,
        subject_cap=subject[:1].upper() + subject[1:],
        mode=mode_phrase,
        pronoun=pronoun,
        pronoun_lower=pronoun_lower,
    )


def render_construction(label: str, subject: str, mode: str, pronoun: str) -> str:
    """
    Fills PHRASE_TEMPLATES[label]. Returns None for a label with no
    template (shouldn't happen -- every CONSTRUCTION_MODE_MAP key has
    one -- but callers shouldn't crash on a label this module doesn't
    know about, e.g. if the map ever grows out of sync with the
    matcher).
    """
    template = PHRASE_TEMPLATES.get(label)
    if not template:
        return None
    return template.format(
        subject=subject or "that",
        mode=mode,
        mode_cap=mode.capitalize(),
        pronoun=pronoun,
        # "I" never lowercases in English, even mid-sentence, unlike
        # you/we/they (was pronoun.lower always,
        # producing "i suppress X" for the Lv/Er axis).
        pronoun_lower=("I" if pronoun == "I" else pronoun.lower()),
    )


# ── 2. NORMALIZATION — fixes the "Cecilia read as apposition" mis-parse ──
def normalize_for_parsing(text: str, character_name: str = None) -> str:
    """
    Inserts a comma+exclamation before a known character name so spaCy's
    dependency parser doesn't fold the danger noun into an apposition of
    the name (found this session with "Watch out Cecilia a monster!").
    Safe no-op if character_name is None/not found in text — proper-name
    handling for OTHER named entities (e.g. "John") is intentionally out
    of scope here, per the author: filled later via the relationship/
    memory layer, not via this parser-level fix.

    FIX 2026-09-10 (found testing "Look, Delia, a monster!" -- returned
    NO subject at all): this used to reconstruct the string by blindly
    gluing on ", {name}! " regardless of what punctuation was already
    sitting right next to the name in the ORIGINAL text -- fine for the
    session's own test case ("Watch out Cecilia a monster!", no existing
    punctuation around "Cecilia" at all), but not idempotent: text that
    ALREADY separates the name with a comma doubled up into
    "Look,, Delia! , a monster!" -- the doubled/dangling commas threw
    spaCy's parse off badly enough that "monster" lost its dependency
    relation entirely and extract_subject() had nothing to grab.
    Stripping any comma/space already touching the split point before
    reassembling makes this safe to run whether or not the input already
    punctuates the name correctly.
    """
    if not character_name or character_name not in text:
        return text
    before, after = text.split(character_name, 1)
    before = before.rstrip(", ").strip()
    after = after.lstrip(", ").strip()
    if after:
        after = after[0].upper() + after[1:]
    return f"{before}, {character_name}! {after}".strip()


# Fix: "a monster" here is an
# appositive ("Delia, a monster!" -- monster restates/points at what
# Delia's being shown), dep="appos", which wasn't in this tuple at all.
# Added after "pobj" (a real relation-anchored candidate should still
# win over a loose appositive when both exist) but before "ROOT" (the
# least specific, last-resort tier).
_SUBJECT_PRIORITY = ("nsubj", "nsubjpass", "dobj", "attr", "pobj", "appos", "ROOT")
_ARTICLE_SKIP = {"that", "this", "it", "you", "i", "we", "they", "he", "she",
                  "here", "there"}


def _add_article(word: str, is_proper: bool) -> str:
    """Prefixes a bare noun with 'the' so it reads as a real object/
    subject instead of a dangling noun ("I suppress bandit" ->
    "I suppress the bandit"). Found 2026-09-09 testing sentence quality
    end to end: extract_subject() never attached an article at all, in
    ANY of its callers (select_axis_response's SENTENCE_TEMPLATES fill
    AND render_construction's 29 templates use the same {subject} slot
    in both subject- and object-grammatical position, so adding it once
    here covers both). Skipped for proper nouns and words that already
    function as a full noun phrase / pronoun.
    """
    if not word or is_proper or word.lower() in _ARTICLE_SKIP:
        return word
    return f"the {word}"


def _is_confirmed_noun(tok) -> bool:
    """True if `tok` (already spaCy-tagged NOUN/PROPN) is actually
    trustworthy as a noun. Found 2026-09-09: spaCy's small model
    sometimes mistags an unfamiliar verb form as a plural noun+ROOT
    ("a snake slithers past" -> "slithers" tagged NOUN/NNS/ROOT, "snake"
    demoted to a "compound" child the old candidate list didn't even
    look at). Cross-checks db_lexicon.py first (already-curated
    biological/non_biological/quality = confirmed noun); for a word the
    5,164-word lexicon doesn't cover, falls back to WordNet: a word with
    zero noun senses but at least one verb sense (true for "slither",
    false for ambiguous real nouns like "shop") is almost certainly a
    verb spaCy mistagged, not a noun to build a sentence around.
    """
    from db.db_lexicon import LEXICON
    word = tok.lemma_.lower()
    entry = LEXICON.get(word) or LEXICON.get(tok.text.lower())
    if entry:
        return entry.get("node_type") in ("biological", "non_biological", "quality")
    from nltk.corpus import wordnet as wn
    noun_senses = len(wn.synsets(word, pos=wn.NOUN))
    verb_senses = len(wn.synsets(word, pos=wn.VERB))
    if noun_senses == 0 and verb_senses > 0:
        return False
    return True


def speaker_to_focus(speaker: str) -> str:
    """
    2026-09-09: the "who's talking" selector -- "narrator" (default,
    reserved keyword, case-insensitive) means
    the focus is still whatever construction_matcher/spaCy extracts from
    the text itself ("a bandit blocks the road" -> "the bandit", same
    machinery as before). Anything ELSE (any character the caller wants
    to add, an open/growing list -- "bandit", "hero", a proper name, or
    the special-cased "user" for the person on the other side
    of the screen) means the speaker's identity IS the focus already --
    no parsing needed, because who's talking was never in question.
    "user" gets no article (matches the literal design example: "smiling
    at user", not "smiling at the user"); a lowercase common-noun-style
    name gets "the" ("bandit" -> "the bandit"); a Capitalized name is
    treated as a proper name and used as-is ("Mark" -> "Mark").
    Returns None for narrator (caller should fall back to text parsing).
    """
    if not speaker or speaker.lower() == "narrator":
        return None
    if speaker.lower() == "user":
        return "user"
    return _add_article(speaker, is_proper=speaker[:1].isupper())


def extract_subject(doc, character_name: str = None, known_names: set = None):
    """
    Best-effort grammatical-subject extraction for filling a closed
    template's {subject} slot. Excludes the character's own name (that's
    who's being addressed, not the thing to react to).

    FIX 2026-09-09 (see the system-state notes §38 pending #6 -- "a cute
    animal runs past picks runs as the subject"): candidates are now checked
    in an explicit dependency-priority order (real subject first, ROOT
    last -- ROOT is the most likely token to actually be the sentence's
    verb) and cross-validated with _is_confirmed_noun() before being
    accepted; a candidate that fails the check but has its own compound
    child defers to that child instead ("snake" recovered from under a
    mistagged "slithers"). Every accepted result gets an article via
    _add_article() -- see that function's docstring.

    `known_names` (found alongside the action-bank subject-mismatch
    report): properness (is_proper, below) was decided purely from
    spaCy's own POS tag (PROPN vs NOUN), which spaCy gets from
    capitalization -- a real name typed in lowercase in the raw text
    ("the bandit attacks joaquin", a narrator typo) is tagged as a
    common NOUN, so _add_article prefixed it: "the joaquin". known_names
    is a {lowercase: canonical-case} lookup of the proper names already
    known to be real in THIS turn (the reacting character, whoever is
    being addressed -- see select_axis_response) -- a case-insensitive
    match against it now overrides spaCy's tag AND restores the
    canonical capitalization, independent of how the word was typed in
    the source text ("joaquin" -> "Joaquin", article skipped).
    """
    known_names = known_names or {}

    def _valid(tok):
        return (tok.pos_ in ("NOUN", "PROPN")
                and (not character_name or tok.text != character_name))

    def _resolve(tok):
        canonical = known_names.get(tok.text.lower())
        if canonical:
            return canonical, True
        return tok.text, tok.pos_ == "PROPN"

    # Fix: the mistagged-ROOT recovery below
    # (compound child of a verb spaCy mistagged as a NOUN/ROOT -- same
    # mechanism already handling "a snake slithers past" -> "snake")
    # only ever ran once the tiered loop REACHED the "ROOT" tier, its
    # last priority. That's fine when nothing else matches first, but
    # here "child" is a perfectly valid pobj (off the "at"-prepphrase
    # that hung off the same mistagged root) and passes
    # _is_confirmed_noun on its own -- it wins the loop at the "pobj"
    # tier before "ROOT" is ever reached, so the sentence's real actor
    # (wolf) loses to what the threat is aimed at (child).
    #
    # Tried gating this early check on `not _is_confirmed_noun(root)`
    # first (matching the existing per-candidate check) -- doesn't work
    # for THIS word: "lunge" genuinely has 2 WordNet noun senses (it's
    # a real fencing term), so the zero-noun-senses heuristic that
    # catches "slither" can't catch "lunge" -- it's actually ambiguous
    # by word identity alone, only the SENTENCE decides which reading
    # is meant here. Used a structural signal instead: a real scene
    # sentence always has a verb somewhere. If NOTHING in the whole
    # doc is tagged VERB/AUX, the verb spaCy was supposed to find got
    # swallowed into a NOUN -- almost certainly the ROOT itself, since
    # that's where a misread main verb lands. Gated on `not
    # has_real_subject` too (belt and suspenders) so a genuinely
    # correct nsubj-bearing parse is never second-guessed.
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    has_real_subject = any(t.dep_ in ("nsubj", "nsubjpass") for t in doc)
    has_any_verb = any(t.pos_ in ("VERB", "AUX") for t in doc)
    if root and not has_real_subject and not has_any_verb and root.pos_ in ("NOUN", "PROPN"):
        compound_kids = [c for c in root.children
                          if c.dep_ == "compound" and _valid(c)]
        if compound_kids:
            child = compound_kids[0]
            text, is_proper = _resolve(child)
            return _add_article(text, is_proper=is_proper)

    by_dep = {}
    for t in doc:
        if _valid(t) and t.dep_ in _SUBJECT_PRIORITY:
            by_dep.setdefault(t.dep_, []).append(t)

    for dep in _SUBJECT_PRIORITY:
        for t in by_dep.get(dep, []):
            if _is_confirmed_noun(t):
                text, is_proper = _resolve(t)
                return _add_article(text, is_proper=is_proper)
            compound_kids = [c for c in t.children
                              if c.dep_ == "compound" and _valid(c)]
            if compound_kids:
                child = compound_kids[0]
                text, is_proper = _resolve(child)
                return _add_article(text, is_proper=is_proper)
            # fails the noun check and has nothing to recover from --
            # skip rather than return a likely-mistagged verb
    return None


# ── 3. DEPENDENCY MATCHER — patterns validated ────────────
def _build_matcher():
    from spacy.matcher import DependencyMatcher
    nlp = get_nlp()
    m = DependencyMatcher(nlp.vocab)

    # #8 Conditional -- advcl + mark="if" (and NOT also "as", see MANNER
    # resolution below -- "as if" would otherwise double-match)
    m.add("CONDITIONAL", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": "if"}},
    ]])

    # #22 Manner -- advcl + mark="as" + mark="if" (more specific than
    # Conditional; wins on the same advcl -- see resolve_constructions())
    m.add("MANNER", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "m_as", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": "as"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "m_if", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": "if"}},
    ]])

    # #18 Purpose -- advcl + mark="so" (the "that" of "so that" is a
    # second mark token on the same advcl, not required for the match)
    m.add("PURPOSE", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": "so"}},
    ]])

    # #4 Opinion -- ccomp hanging off an opinion verb ("that" optional)
    m.add("OPINION", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": {"IN": ["think", "believe", "guess", "suppose"]}}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
    ]])

    # #29 Indirect interrogative -- ccomp + mark="if"/"whether"
    m.add("INDIRECT_Q", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
        {"LEFT_ID": "comp", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": {"IN": ["if", "whether"]}}},
    ]])

    # #13 Subordination -- csubj hanging off a non-"be" ROOT, no ccomp
    # on that ROOT (disambiguates from #15 Metalinguistic below --
    # confirmed via spaCy's parser: "What they told me doesn't
    # make sense" has csubj->make, no ccomp; "What I mean IS, it
    # doesn't matter" has csubj->is AND ccomp->is).
    m.add("SUBORDINATION", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": {"NOT_IN": ["be"]}}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "sub", "RIGHT_ATTRS": {"DEP": "csubj"}},
    ]])

    # #15 Metalinguistic -- "What I mean is, ..." -- csubj + ccomp both
    # hanging off a "be" ROOT
    m.add("METALINGUISTIC", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": "be"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "sub", "RIGHT_ATTRS": {"DEP": "csubj"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
    ]])

    # #7 Causal / #9 Concessive / #10 Temporal -- same advcl+mark shape
    # as Conditional/Purpose/Manner above, different mark vocabulary
    m.add("CAUSAL", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": {"IN": ["because", "since"]}}},
    ]])
    m.add("CONCESSIVE", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": "mark", "LOWER": {"IN": ["although", "though"]}}},
    ]])
    m.add("TEMPORAL", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adv", "RIGHT_ATTRS": {"DEP": "advcl"}},
        {"LEFT_ID": "adv", "REL_OP": ">", "RIGHT_ID": "mark", "RIGHT_ATTRS": {"DEP": {"IN": ["mark", "advmod"]}, "LOWER": {"IN": ["when", "while", "before", "after"]}}},
    ]])

    # #21 Result -- "so" (advmod) + ADJ, with the ccomp (mark="that")
    # hanging either off the ADJECTIVE (well-punctuated input: "It was
    # so overwhelming that it gave up") or off the ROOT verb directly
    # (observed: the small model re-attaches ccomp to ROOT
    # when the sentence lacks a trailing period -- common in roleplay
    # text that skips punctuation). Two patterns, same label.
    m.add("RESULT", [[
        {"RIGHT_ID": "adj", "RIGHT_ATTRS": {"DEP": {"IN": ["acomp", "attr"]}}},
        {"LEFT_ID": "adj", "REL_OP": ">", "RIGHT_ID": "so", "RIGHT_ATTRS": {"DEP": "advmod", "LOWER": "so"}},
        {"LEFT_ID": "adj", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
    ]])
    m.add("RESULT", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adj", "RIGHT_ATTRS": {"DEP": {"IN": ["acomp", "attr"]}}},
        {"LEFT_ID": "adj", "REL_OP": ">", "RIGHT_ID": "so", "RIGHT_ATTRS": {"DEP": "advmod", "LOWER": "so"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
    ]])

    # #5 Simple connector -- cc + conj both hanging off ROOT
    m.add("SIMPLE_CONNECTOR", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "cc", "RIGHT_ATTRS": {"DEP": "cc"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "conj", "RIGHT_ATTRS": {"DEP": "conj"}},
    ]])

    # #11 Explanatory -- "The thing is (that) ..." -- nsubj lemma="thing"
    m.add("EXPLANATORY", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": "be"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "subj", "RIGHT_ATTRS": {"DEP": "nsubj", "LEMMA": "thing"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "comp", "RIGHT_ATTRS": {"DEP": "ccomp"}},
    ]])

    # #19 Comparative -- JJR (comparative adj) + "than" prep + pobj
    m.add("COMPARATIVE", [[
        {"RIGHT_ID": "adj", "RIGHT_ATTRS": {"TAG": "JJR"}},
        {"LEFT_ID": "adj", "REL_OP": ">", "RIGHT_ID": "than", "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "than"}},
        {"LEFT_ID": "than", "REL_OP": ">", "RIGHT_ID": "np2", "RIGHT_ATTRS": {"DEP": "pobj"}},
    ]])

    # #23/#24 Restrictive vs. non-restrictive relative -- same base
    # pattern (noun + relcl child); resolve_constructions below
    # relabels to NON_RESTRICTIVE_RELATIVE if a comma sits right before
    # the relative clause (confirmed via spaCy's parser: the comma
    # is a punct token whose head is the noun, positioned right before
    # the relcl's subject).
    m.add("RESTRICTIVE_RELATIVE", [[
        {"RIGHT_ID": "noun", "RIGHT_ATTRS": {"POS": "NOUN"}},
        {"LEFT_ID": "noun", "REL_OP": ">", "RIGHT_ID": "rel", "RIGHT_ATTRS": {"DEP": "relcl"}},
    ]])

    # #2 Experiential -- pronoun subject + perception verb + dobj
    m.add("EXPERIENTIAL", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": {"IN": ["feel", "see", "hear", "notice", "sense", "perceive"]}}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "subj", "RIGHT_ATTRS": {"DEP": "nsubj", "POS": "PRON"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "obj", "RIGHT_ATTRS": {"DEP": "dobj"}},
    ]])

    # #3 Evaluative -- two shapes: copula+ADJ ("It's not that important")
    # or evaluation-verb+dobj ("I like that dog")
    m.add("EVALUATIVE", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": "be"}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "adj", "RIGHT_ATTRS": {"DEP": "acomp", "POS": "ADJ"}},
    ]])
    m.add("EVALUATIVE", [[
        {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT", "LEMMA": {"IN": ["like", "hate", "love", "dislike", "admire"]}}},
        {"LEFT_ID": "root", "REL_OP": ">", "RIGHT_ID": "obj", "RIGHT_ATTRS": {"DEP": "dobj"}},
    ]])

    # PENDING as DependencyMatcher patterns (handled instead by
    # _lexical_and_order_checks() below, since DependencyMatcher can't
    # express "absence of a child" or linear word-order constraints):
    # #1 Existential, #6 Negation, #12 Reordered, #14 Hypothetical
    # (disambiguated from #8 post-match), #16 Nuance, #20 Superlative,
    # #25 Passive voice, #26 Imperative, #27 Exclamative,
    # #28 Direct interrogative, #30 Discourse connector.
    return m


_HEDGE_PHRASES = ("in a way", "sort of", "kind of", "somewhat", "a bit")
_DISCOURSE_CONNECTORS = {"however", "nevertheless", "still", "yet", "though", "otherwise"}


def _lexical_and_order_checks(doc, text: str):
    """
    Constructions that need lexical lookup, absence-of-child, or linear
    word-order -- none of which DependencyMatcher can express directly.
    Returns a list of labels, same shape as resolve_constructions()'s
    DependencyMatcher half.
    """
    found = []
    lowered = text.lower().strip()

    # #16 Nuance -- hedge phrase at/near the start
    if any(lowered.startswith(h) or f" {h} " in lowered for h in _HEDGE_PHRASES):
        found.append("NUANCE")

    # #30 Discourse connector -- sentence opens with a discourse adverb
    first = doc[0] if len(doc) else None
    if first and first.dep_ == "advmod" and first.lower_ in _DISCOURSE_CONNECTORS:
        found.append("DISCOURSE_CONNECTOR")

    # #1 Existential -- expletive "there"
    if any(t.dep_ == "expl" for t in doc):
        found.append("EXISTENTIAL")

    # #25 Passive voice -- nsubjpass present
    if any(t.dep_ == "nsubjpass" for t in doc):
        found.append("PASSIVE_VOICE")

    # #20 Superlative -- JJS tag anywhere
    if any(t.tag_ == "JJS" for t in doc):
        found.append("SUPERLATIVE")

    # #6 Negation -- neg dependency on the ROOT's subtree
    if any(t.dep_ == "neg" for t in doc):
        found.append("NEGATION")

    # #26 Imperative -- base-form ROOT verb (VB) with no nsubj/nsubjpass
    # child at all, and the sentence isn't a question
    roots = [t for t in doc if t.dep_ == "ROOT"]
    if roots and roots[0].tag_ == "VB" and not any(
        t.dep_ in ("nsubj", "nsubjpass") for t in doc
    ) and not lowered.rstrip("!").endswith("?"):
        found.append("IMPERATIVE")

    # #27 Exclamative -- "What/How ...!" with no finite verb ROOT
    if lowered.rstrip().endswith("!") and first and first.lower_ in ("what", "how") \
            and roots and roots[0].pos_ != "VERB":
        found.append("EXCLAMATIVE")

    # #28 Direct interrogative -- aux/verb precedes its own subject
    # (inversion), ends in "?", and it's NOT a wh-question (no WP/WRB/
    # WDT tag anywhere -- those are #28's cousins, not this one)
    has_wh = any(t.tag_ in ("WP", "WP$", "WDT", "WRB") for t in doc)
    if lowered.rstrip().endswith("?") and not has_wh:
        for t in doc:
            if t.dep_ in ("nsubj", "nsubjpass"):
                aux_before = [a for a in doc if a.dep_ in ("aux", "auxpass") and a.head == t.head and a.i < t.i]
                if aux_before:
                    found.append("DIRECT_Q")
                break

    # #12 Reordered -- a prep/advcl/advmod adjunct of ROOT sits BEFORE
    # the subject in linear order (normal English is Subject-first).
    # Fix: only checked prep/advcl, missing a
    # fronted single-word adverb ("Right there, I fight it." -- "there"
    # is advmod, not prep/advcl). Confirmed via spaCy's own parse before
    # adding it, not guessed.
    for t in doc:
        if t.dep_ == "ROOT":
            subj = next((c for c in t.children if c.dep_ in ("nsubj", "nsubjpass")), None)
            fronted = next((c for c in t.children if c.dep_ in ("prep", "advcl", "advmod") and subj and c.i < subj.i), None)
            if subj and fronted:
                found.append("REORDERED")
            break

    return found


def resolve_constructions(doc, text: str = ""):
    """
    Runs the DependencyMatcher, resolves same-clause overlaps by
    specificity (MANNER beats CONDITIONAL, HYPOTHETICAL relabels
    CONDITIONAL when the advcl carries a past-perfect "had", NON_
    RESTRICTIVE relabels RESTRICTIVE when a comma sits right before the
    relative clause), then adds the lexical/order-based checks that
    DependencyMatcher can't express. Returns a list of construction
    labels (may be empty for input that matches none of the 29).
    """
    global _matcher
    if _matcher is None:
        _matcher = _build_matcher()
    nlp = get_nlp()

    matches = _matcher(doc)
    by_clause = {}
    for match_id, tokens in matches:
        label = nlp.vocab.strings[match_id]
        # anchor index: every pattern's 2nd node (index 1) is its clause/
        # adjective anchor, EXCEPT RESULT's short variant (3 nodes: adj,
        # so, comp), where "adj" is declared first (index 0). RESULT's
        # long variant (4 nodes: root, adj, so, comp) puts "adj" at
        # index 1 like everything else.
        if label == "RESULT":
            anchor_idx = 0 if len(tokens) == 3 else 1
        else:
            anchor_idx = 1
        clause_idx = tokens[anchor_idx]  # plain int key -- avoids Token hash/equality quirks across calls
        by_clause.setdefault(clause_idx, []).append((label, tokens))

    resolved = []
    for clause_idx, entries in by_clause.items():
        clause_tok = doc[clause_idx]
        labels = [e[0] for e in entries]

        if "MANNER" in labels:
            resolved.append("MANNER")
            continue

        if "RESULT" in labels:
            resolved.append("RESULT")
            continue

        if "CONDITIONAL" in labels:
            # #14 Hypothetical: the advcl has an aux with Tense=Past
            # (i.e. "had") -- past-perfect, not a real/future conditional
            has_had = any(
                a.dep_ == "aux" and "Past" in a.morph.get("Tense")
                for a in clause_tok.children
            )
            resolved.append("HYPOTHETICAL" if has_had else "CONDITIONAL")
            continue

        if "RESTRICTIVE_RELATIVE" in labels:
            # #24 Non-restrictive: a comma sits immediately before the
            # relative clause's own subject token
            rel_tok = next(doc[toks[1]] for l, toks in entries if l == "RESTRICTIVE_RELATIVE")
            has_comma = any(t.text == "," and t.i < rel_tok.i and t.head == rel_tok.head for t in doc)
            resolved.append("NON_RESTRICTIVE_RELATIVE" if has_comma else "RESTRICTIVE_RELATIVE")
            continue

        resolved.append(labels[0])

    resolved.extend(_lexical_and_order_checks(doc, text or doc.text))

    # Safety net: RESULT and EVALUATIVE(cop) match the same acomp node
    # ("It was so loud that..." is also "It was [ADJ]"), and grouping
    # by index sometimes fails to join them in the same
    # by_clause entry. It is checked directly on the doc: if there is an
    # adj with "so" (advmod) + its own ccomp, it is RESULT, not EVALUATIVE.
    if "EVALUATIVE" in resolved and "RESULT" not in resolved:
        for t in doc:
            if t.dep_ in ("acomp", "attr") and any(
                c.dep_ == "advmod" and c.lower_ == "so" for c in t.children
            ) and any(c.dep_ == "ccomp" for c in t.children):
                resolved = ["RESULT" if r == "EVALUATIVE" else r for r in resolved]
                break

    return resolved


# ── 4. QUESTION GENERATION BY PRONOUN REFLECTION (ELIZA-style) ─────────
# For when the winning mode needs the character to ask something back
# (Observe/#28 or Investigate/#29 -- the only 2 modes with an
# interrogative construction in the whole 30, both on North -- see
# the design notes "why only North asks").
_PRONOUN_REFLECT = {"you": "I", "your": "my", "yours": "mine", "yourself": "myself"}

# KNOWN LIMIT (observed): modals (should/can/will...) don't
# change form with person, so plain text-swap works for them -- but
# "to be" DOES change (you are -> I am, you were -> I was). This table
# is the fix; extend if other person-sensitive aux forms show up.
_BE_REFLECT = {"are": "am", "were": "was"}


def _reflect_aux(doc, root):
    parts = []
    for t in doc:
        if t.dep_ in ("aux", "neg") and t.head == root:
            parts.append(_BE_REFLECT.get(t.text.lower(), t.text))
    return "".join(parts)


def make_why_question(sent: str) -> str | None:
    """'You shouldn't do that!' -> 'Why shouldn't I do that?'
    Keeps the object literal -- reads as a challenge/defiance (Attack-
    flavored), not genuine curiosity. See make_what_question() below for
    the other kind.

    FIX (found alongside the action-bank subject-mismatch report): only
    _PRONOUN_REFLECT has an actual you->I mapping, so this function's
    whole premise -- "someone is addressing Delia directly" -- only
    holds when the sentence's own grammatical subject IS one of those
    words. Before this guard, ANY nsubj got used literally
    (subj_text = subj.text, since .get() falls back to the word itself
    for anything not in the table) -- "that bandit looks dangerous"
    produced a "question" built around "bandit", not a reflection of
    anyone, while the caller (select_axis_response) had already pinned
    `subject` to forced_focus (the speaker) for the SAME turn: dialogue
    about the bandit, {subject}-filled action about the speaker,
    talking about two different things. Bailing out here (same as the
    existing "no roots/subjs" bail) sends the caller to the normal
    subject+verb bank instead, which correctly and consistently uses
    `subject` (forced_focus) in both the sentence and the action line.
    """
    nlp = get_nlp()
    doc = nlp(sent.rstrip("!.?"))
    roots = [t for t in doc if t.dep_ == "ROOT"]
    subjs = [t for t in doc if t.dep_ == "nsubj"]
    if not roots or not subjs or subjs[0].text.lower() not in _PRONOUN_REFLECT:
        return None
    root, subj = roots[0], subjs[0]
    subj_text = _PRONOUN_REFLECT[subj.text.lower()]
    aux_text = _reflect_aux(doc, root)
    rest = [t.text for t in doc
            if t.dep_ not in ("aux", "neg", "nsubj", "punct") and t != root]
    return f"Why {aux_text} {subj_text} {' '.join([root.text] + rest)}?".replace("  ", " ")


def make_what_question(sent: str) -> str | None:
    """'You shouldn't do that!' -> 'What shouldn't I do?'
    Replaces the object with 'what' -- genuine information gap
    (Investigate-flavored), not a rhetorical challenge. Returns None if
    there's no direct object to replace (e.g. intransitive verbs like
    "leave"/"understand" in "You can't leave!") -- that sentence only
    supports make_why_question().

    Same guard and same reasoning as make_why_question() above --
    see that docstring's FIX note.
    """
    nlp = get_nlp()
    doc = nlp(sent.rstrip("!.?"))
    roots = [t for t in doc if t.dep_ == "ROOT"]
    subjs = [t for t in doc if t.dep_ == "nsubj"]
    dobjs = [t for t in doc if t.dep_ == "dobj"]
    if not roots or not subjs or not dobjs or subjs[0].text.lower() not in _PRONOUN_REFLECT:
        return None
    root, subj = roots[0], subjs[0]
    subj_text = _PRONOUN_REFLECT[subj.text.lower()]
    aux_text = _reflect_aux(doc, root)
    return f"What {aux_text} {subj_text} {root.text}?".replace("  ", " ")


def best_construction_for_axis(constructions: list, axis: str):
    """
    Of whatever construction labels resolve_constructions() matched,
    returns the first one that actually belongs to the current axis
    (a matched CONDITIONAL only helps a North/V-P response -- it's
    meaningless for a South/West/East mode this cycle). None if nothing
    matched belongs to this axis (most cycles, until more constructions
    have templates written for edge cases the current 29 don't cover).
    """
    for label in constructions:
        entry = CONSTRUCTION_MODE_MAP.get(label)
        if entry and entry[1] == axis:
            return label
    return None


# ── 5. HIGH-LEVEL ENTRY POINT ───────────────────────────────────────────
def analyze_input(text: str, character_name: str = None, known_names: dict = None) -> dict:
    """
    One call for cycle_manager_v5.py: normalizes, parses, extracts the
    subject, and resolves whichever constructions matched. Returns a
    dict -- callers cross `constructions` against CONSTRUCTION_MODE_MAP
    if they need the (axis, mode) for a matched construction number
    (this function doesn't do that lookup itself since a label like
    "CONDITIONAL" maps to 2 numbers in the docx in general -- callers
    already know which axis/category they're building for).

    known_names: see extract_subject()'s docstring -- a
    {lowercase: canonical-case} lookup of names to treat as proper even
    if spaCy's POS tagger didn't (a name typed in lowercase in the raw
    text). Passed straight through.
    """
    nlp = get_nlp()
    normalized = normalize_for_parsing(text, character_name)
    doc = nlp(normalized)
    return {
        "normalized_text": normalized,
        "subject": extract_subject(doc, character_name, known_names),
        "constructions": resolve_constructions(doc, normalized),
        "doc": doc,
    }
