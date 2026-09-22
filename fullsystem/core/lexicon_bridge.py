# core/lexicon_bridge.py — UNIQUE HOST
#
# LEXICON → RAW AXIS PUSH (closes part of pending #1: "connect the
# real lexicon to vec_s" — see the system-state notes).
#
# HONEST FINDING FIRST (read this before trusting the numbers below):
# ──────────────────────────────────────────────────────────────────
# The two axis dimensions are NOT symmetric in how much real data backs
# them today:
#
#   - V/I (Viability/Inviability = Benefit vs Danger, i.e. VALENCE —
#     "is this good or bad") only has real signal from the small
#     HAND-CURATED lists in db/db_axis_lexicon.py: AXIS_NORTH (~43 words:
#     hopeful modal verbs, future-oriented concepts, affirmatives) and
#     AXIS_SOUTH (~65 words: negation, failure/past concepts, refusal
#     exclamations) + INHERENTLY_NEGATIVE_VERBS (13 words). That is it.
#     ~120 words total carry valence.
#
#   - Lv/Gv (Local/Global = personal-sensory vs abstract-rational, i.e.
#     SCOPE, not valence) has real signal at scale: the auto-generated
#     db/db_axis_lexicon_generated.py ADJECTIVES_EAST/WEST (144+372
#     words from WordNet) plus the hand AXIS_EAST/WEST sensory and
#     evaluative-category lists. But — checked directly — these lists
#     mix positive AND negative words together with no sign (e.g.
#     moral_value contains BOTH "good" and "bad"). They tell you
#     WHETHER a word is personal/sensory or abstract/evaluative, never
#     whether it's good or bad.
#
# CONSEQUENCE: for the ~4,900 nouns/verbs in db/db_lexicon.py (which only
# carries WordNet semantic CATEGORY — "danger" is tagged category=state,
# not "bad") and for most of the ~5,000 adjectives once scope-classified,
# there is currently NO automatic signal telling the system whether they
# push toward Benefit or Danger. Only ~120 hand-curated words do.
#
# WHAT THIS FILE DOES with that honestly: builds a real (not simulated)
# word -> axis push table from every source that DOES carry usable
# signal, so today's ~120 valence words + the East/West scope words
# actually reach vec_s instead of sitting unused. It does NOT invent
# valence for words that don't have it — an adjective that's only
# scope-classified (e.g. "loud", "beautiful") pushes Lv or Gv but
# contributes nothing to the Danger-vs-Benefit decision, which is
# accurate to what we actually know about that word today.
#
# NEXT STEP this exposes (not done here): to make Danger/Benefit
# resolve automatically for the bulk of the lexicon, the missing piece
# is a real sentiment source (e.g. SentiWordNet, or hand-tagging the
# ~5,000 db_lexicon.py entries with a +/-/0 valence sign) — see
# the system-state notes item 6, this is the same gap, seen from the
# chemical side instead of the "596 unclassified adjectives" side.

from db.db_axis_lexicon import (
    AXIS_NORTH, AXIS_SOUTH, AXIS_EAST, AXIS_WEST,
    INHERENTLY_NEGATIVE_VERBS, POSSIBILITY_DAMPENERS,
)
from db.db_axis_lexicon_generated import ADJECTIVES_EAST, ADJECTIVES_WEST

# Sub-lists that are grammar/pronoun helpers, not valence or scope
# content — excluded so "we"/"you"/"what" don't get treated as pushing
# an axis (that's the Social Positioning system's job, a separate
# concern — core/response_matrix.py SOCIAL_POSITIONING).
_SKIP_SUBCATEGORIES = {"subjects", "interrogatives"}

# weight = how confident this source is (1.0 = clear valence word,
# 0.4-0.5 = scope-only, no sign — kept lower on purpose, see docstring)
_WORD_AXIS_PUSH = {}


def _register(words, axis, weight, source):
    for w in words:
        w = w.lower().strip()
        if not w or " " in w:
            continue  # skip multi-word phrases (e.g. "of course") — token-level lookup only
        # first source to claim a word wins (valence sources registered first)
        if w not in _WORD_AXIS_PUSH:
            _WORD_AXIS_PUSH[w] = {"axis": axis, "weight": weight, "source": source}


# ── VALENCE sources (real Danger/Benefit signal) — registered first, wins ties ──
for _cat, _words in AXIS_NORTH.items():
    if _cat not in _SKIP_SUBCATEGORIES:
        _register(_words, "V", 1.0, f"axis_north.{_cat}")

for _cat, _words in AXIS_SOUTH.items():
    if _cat not in _SKIP_SUBCATEGORIES:
        _register(_words, "I", 1.0, f"axis_south.{_cat}")

_register(INHERENTLY_NEGATIVE_VERBS, "I", 0.8, "inherently_negative_verbs")

# ── SCOPE-ONLY sources (Lv/Gv personal-vs-abstract, no valence sign) ──
for _cat, _words in AXIS_EAST.items():
    if _cat not in _SKIP_SUBCATEGORIES:
        _register(_words, "Lv", 0.5, f"axis_east.{_cat}")

for _cat, _words in AXIS_WEST.items():
    if _cat not in _SKIP_SUBCATEGORIES:
        _register(_words, "Gv", 0.5, f"axis_west.{_cat}")

# Auto-generated (WordNet, ~5,000 adjectives) — lower weight than the
# hand-curated East/West lists since these are the least-reviewed source
_register(ADJECTIVES_EAST, "Lv", 0.4, "adjectives_east_generated")
_register(ADJECTIVES_WEST, "Gv", 0.4, "adjectives_west_generated")

_DAMPENER_WORDS = {w.lower() for w in POSSIBILITY_DAMPENERS}

_UNIT_PUSH = 12.0  # push contributed per matched word at weight 1.0, before dampening/clamping


def lexicon_word_lookup(word: str):
    """Single-word lookup — returns the {'axis','weight','source'} entry or None. Mainly for debugging/demos."""
    return _WORD_AXIS_PUSH.get(word.lower().strip())


def lexicon_axis_push(tokens):
    """
    Real (not simulated) word -> raw axis push, built from the actual
    lexicon files (see module docstring for exactly which words carry
    real signal today). Returns a dict with SOMATIC_KEYS (V,I,Lv,Gv) plus
    debug metadata, or None if nothing in `tokens` matched anything.

    This is additive/independent from db/db_concepts.py's hand-authored
    concept pipeline (core/pre_input.py) — motors/cycle_manager_v5.py
    combines both via core.formulas.apply_input() so a scene can be
    informed by BOTH a hand-authored concept (e.g. "ghost") AND any
    lexicon word with real axis signal (e.g. "hope", "never") at once.
    """
    from db.db_somatic import SOMATIC_KEYS, SOMATIC_MAX

    vec = {k: 0.0 for k in SOMATIC_KEYS}
    matched = []
    dampened = False

    for token in tokens:
        token = token.lower().strip()
        if token in _DAMPENER_WORDS:
            dampened = True
            continue
        entry = _WORD_AXIS_PUSH.get(token)
        if not entry:
            continue
        vec[entry["axis"]] += _UNIT_PUSH * entry["weight"]
        matched.append((token, entry["axis"], entry["source"]))

    if not matched:
        return None

    if dampened:
        # POSSIBILITY_DAMPENERS ("might", "could", "perhaps"...) softens
        # whatever else was read this cycle — modal uncertainty, not a
        # vertex of its own.
        for k in vec:
            vec[k] *= 0.6

    for k in vec:
        vec[k] = min(SOMATIC_MAX, vec[k])

    vec["_matched_words"] = matched
    vec["_dampened"]      = dampened
    vec["_pipeline"]      = "lexicon"
    return vec
