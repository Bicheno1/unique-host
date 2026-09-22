# character/tree_questionnaire.py — UNIQUE HOST
#
# Walks db/db_category_words.py (character/category_tree.py's nodes,
# already expanded into real member words by tools/expand_category.py)
# and generates ONE 1-10 question per node that has words attached —
# this is the "world/likes tree" questionnaire proper, separate from
# the hand-picked family_opinion/animals_opinion/core_fear/core_comfort
# in character/questionnaire.py (which stay: "family" as a relational
# role and free-text fear/comfort have no WordNet anchor, so the tree
# can't reach them automatically — this only covers what
# tools/expand_category.py actually resolved, ~867 words / 27 nodes).
#
# CASCADE (confirmed, character/valence.py:refine_chain,
# w=0.7): a word can sit under more than one answered node at once
# (e.g. "dog" is under the general ("biological","animal") node AND
# the more specific ("biological","animal","diet","carnivore") and
# ("...","domestication","domestic") leaves). Every applicable answer
# for that word gets chained shallowest-to-deepest through
# refine_chain — general sets the base, each deeper/more specific
# answer refines it further, none of them overwrite outright.
#
# node_type gating (character/valence.py:compute_concept_push): a
# word's own top-level type (path[0] -- "biological" or
# "non_biological") decides whether its value pulls Gv/Rr (biological)
# or Lv/Er (non_biological) -- same rule as the hand-picked concepts.

from lexicon_db.db_category_words import CATEGORY_WORDS
from questionnaire.valence import compute_concept_push, refine_chain

QUESTION_PREFIX = "tree__"

# Hand-written labels for the new branches.
try:
    from lexicon_db.db_category_words_extra import EXTRA_LABELS
except ImportError:
    EXTRA_LABELS = {}


def _question_key(path: tuple) -> str:
    return QUESTION_PREFIX + "__".join(path)


def _label_for_path(path: tuple) -> str:
    """Human-readable question text. Depth 2 (type, subtype) asks about
    the whole subtype in general; deeper paths ask about that specific
    facet leaf. Good enough as a first pass -- meant to be hand-edited
    per node once reviewed, same as any other generated draft in this
    project.

    2026-09-15: action/quality subtypes (from lexicon_subtype, no
    facets underneath) read badly with the noun-shaped phrasing below
    ("how do they feel about personalitys/communications in general?"
    -- broken plural, and "communications" reads as objects/mail, not
    as the ACT of communicating). Branch on path[0] instead.
    """
    if path in EXTRA_LABELS:
        return EXTRA_LABELS[path]
    subtype = path[1].replace("_", " ")
    if path[0] == "action":
        verb_subtype = "feeling" if subtype == "emotion verbs" else subtype
        if len(path) == 2:
            return f"How do they feel about {verb_subtype}-related actions in general (e.g. verbs of {verb_subtype})? (1=dislike/avoid, 10=drawn to it)"
        leaf = path[-1].replace("_", " ")
        return f"More specifically, how do they feel about {leaf} {verb_subtype} actions? (1=dislike/avoid, 10=drawn to it)"
    if path[0] == "quality":
        return f"How do they feel about {subtype} qualities/traits in others (e.g. being described that way)? (1=dislike, 10=admire)"
    if len(path) == 2:
        uncountable = {"clothing", "furniture pieces", "equipment"}
        noun = subtype if subtype in uncountable else f"{subtype}s"
        return f"How do they feel about {noun} in general? (1=dislike, 10=love)"
    leaf = path[-1].replace("_", " ")
    return f"More specifically, how do they feel about {leaf} {subtype}s? (1=dislike, 10=love)"


def generate_tree_questions():
    """Returns a list of (key, label, type, extra) tuples, same shape as
    character/questionnaire.py's QUESTIONS -- one per CATEGORY_WORDS
    node that actually has at least one word (skips the empty
    herbivore/toxic-plant leaves, and anything with no wordnet_anchor
    at all, which never made it into CATEGORY_WORDS in the first
    place)."""
    questions = []
    for path, words in CATEGORY_WORDS.items():
        if not words:
            continue
        questions.append((
            _question_key(path),
            _label_for_path(path),
            "slider",
            {"minimum": 1, "maximum": 10, "value": 5},
        ))
    return questions


TREE_QUESTIONS = generate_tree_questions()


def _compute_word_valences(answers: dict):
    """Shared helper for populate_tree_concepts() and compile_related():
    for every word CATEGORY_WORDS knows about that got at least one
    answer, returns {word: (final_value, top_type, [branch_paths])} --
    final_value already cascaded general->specific via refine_chain(),
    top_type is path[0] ("biological"/"non_biological"), and
    branch_paths is every CATEGORY_WORDS path this word appears under
    (used by compile_related() for the "shared branch" condition)."""
    word_answers: dict[str, list] = {}
    word_top_type: dict[str, str] = {}
    word_branches: dict[str, list] = {}

    for path, words in CATEGORY_WORDS.items():
        key = _question_key(path)
        for w in words:
            word_branches.setdefault(w, []).append(path)
            word_top_type.setdefault(w, path[0])
        if key not in answers:
            continue
        value = float(answers[key])
        for w in words:
            word_answers.setdefault(w, []).append((len(path), value))

    result = {}
    for word, entries in word_answers.items():
        entries.sort(key=lambda e: e[0])
        values = [v for _, v in entries]
        final_value = refine_chain(values) if len(values) > 1 else values[0]
        result[word] = (final_value, word_top_type[word], word_branches[word])
    return result


def populate_tree_concepts(answers: dict, fortitude_1_10: dict):
    """Given questionnaire answers (only the tree__... keys matter here)
    and the character's Fortitude, returns (concepts_seed,
    tag_values_seed) covering every word CATEGORY_WORDS knows about,
    refined general->specific per word via refine_chain().

    Words the questionnaire wasn't asked about (no tree__ answer key
    present for any of their nodes) are skipped entirely -- they keep
    whatever default/no push they'd otherwise have, same as before this
    system existed.
    """
    concepts_seed = {}
    tag_values_seed = {"somatic": {}, "mental": {}}

    # Fix: "type" used to be fixed to "subject" no matter
    # whether the word came from a noun/verb/adjective branch -- same
    # bug that had already been fixed in questionnaire.py's
    # _add_valenced_concept (see the compiler README). With the new
    # lexicon, top_type can now be biological/non_biological/
    # action/quality (before, only biological/non_biological existed
    # in the tree), so the same mapping is needed here.
    _TOP_TYPE_TO_CONCEPT_TYPE = {
        "biological":     "subject",
        "non_biological": "object",
        "action":         "action",
        "quality":        "quality",
    }

    for word, (final_value, top_type, _branches) in _compute_word_valences(answers).items():
        biological = (top_type == "biological")
        push = compute_concept_push(fortitude_1_10, final_value, biological)
        tag = f"valence__{word}"
        tag_values_seed["somatic"][tag] = push["somatic"]
        tag_values_seed["mental"][tag]  = push["mental"]
        concepts_seed[word] = {
            "sense": "sight",
            "type": _TOP_TYPE_TO_CONCEPT_TYPE.get(top_type, "subject"),
            "subtype": top_type,
            "synonyms": [word],
            "related": {"valence": {"somatic": [tag], "mental": [tag]}},
        }

    return concepts_seed, tag_values_seed


# ── PROTOTYPE — "related" compiler ( of the state doc) ───────────────
#
# Two conditions, both required (confirmed -- neither alone
# is enough: coffee and family can land at a similar overall value
# without being related; two words in the same branch with wildly
# different values -- love vs. fear of the same category -- aren't
# related either):
#
#   1. SIMILAR VALUE  -- |value_A - value_B| <= VALUE_THRESHOLD (1-10 scale)
#   2. SHARED BRANCH  -- both words appear under the exact same
#                        CATEGORY_WORDS path (real conceptual
#                        association, from the tree structure itself,
#                        not a numeric coincidence)
#
# The branch path itself becomes the shared `related` key, so
# core/pre_input.py:_get_multiplier -- which already works by
# intersecting the SET of `related` keys between concepts active in the
# same scene -- picks this up with no changes on its end. Two words
# sharing a branch key get a coincidence match when they co-occur; two
# words that only coincidentally land at a similar value with no shared
# branch never will.
#
# This is a first pass: O(words^2) within each branch (fine for a
# prototype -- branches here top out at ~290 words), no attempt yet at
# collapsing near-identical branches (e.g. a word related via BOTH
# ("...","animal") and ("...","animal","diet","carnivore") gets two
# separate keys, one per branch, rather than being merged into one).

VALUE_THRESHOLD = 2.0


def compile_related(answers: dict):
    """Returns {word: {branch_key: {"somatic": [tag], "mental": [tag]}}}
    -- extra `related` entries to merge into each word's concepts_seed
    node (see character/questionnaire.py, which merges this into the
    "valence"-only related dict populate_tree_concepts() already built).
    """
    from collections import defaultdict

    word_data = _compute_word_valences(answers)
    branch_to_words = defaultdict(list)
    for word, (_value, _top_type, branches) in word_data.items():
        for path in branches:
            branch_to_words[path].append(word)

    extra_related = defaultdict(dict)
    for path, words in branch_to_words.items():
        if len(words) < 2:
            continue
        key = "shared__" + "__".join(path)
        for i, w1 in enumerate(words):
            v1 = word_data[w1][0]
            for w2 in words[i + 1:]:
                v2 = word_data[w2][0]
                if abs(v1 - v2) <= VALUE_THRESHOLD:
                    extra_related[w1][key] = {"somatic": [f"valence__{w1}"], "mental": [f"valence__{w1}"]}
                    extra_related[w2][key] = {"somatic": [f"valence__{w2}"], "mental": [f"valence__{w2}"]}

    return dict(extra_related)
