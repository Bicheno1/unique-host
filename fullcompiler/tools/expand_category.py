# tools/expand_category.py — UNIQUE HOST
#
# Expands character/category_tree.py nodes' `wordnet_anchor` into lists
# of real member words, by walking WordNet's hyponym closure.
#
# Two filters keep the output clean (added after finding real
# noise in the first pass — see below):
#
#   1. LEXICON KEY MEMBERSHIP — a hyponym's lemma must be a top-level
#      KEY in db/db_lexicon.py, not merely present somewhere in some
#      other word's synonym list. First version matched against the
#      full synonym pool too, which let obscure/scientific synonyms
#      leak in (e.g. "ophidian"/"canis_familiaris" appeared under
#      reptile/dog only because they're listed as synonyms of
#      "snake"/"dog" — neither is itself a common-word lexicon entry).
#
#   2. CATEGORY CROSS-CHECK — a matched word's OWN, independently
#      assigned `category` in db_lexicon.py must belong to the set
#      expected for that branch (SUBTYPE_LEXICON_CATEGORIES below).
#      WordNet's hyponym relation is polysemy-blind: "blue"/"copper"/
#      "emperor"/"soldier"/"miller" are all real hyponyms of insect
#      species (a butterfly, a moth, an ant caste...) but the LEXICON's
#      own classification correctly puts them under quality/substance/
#      person — nothing to do with insects for a real reader. Requiring
#      agreement between "found via this branch's hyponyms" AND
#      "independently classified as this branch's category" filters
#      almost all of this out.
#
# Both intermediate nodes (e.g. "animal" itself, anchor animal.n.01)
# AND leaf facet-options (e.g. "herbivore", anchor herbivore.n.01) get
# expanded — not just leaves — since a general-level anchor also
# carries real, useful words (walk_leaves from category_tree.py only
# visits true leaves, so this file has its own traversal, below).
#
# Leaves with wordnet_anchor=None (relational roles, raw adjective
# facets, CCM-specific concepts) have no clean WordNet equivalent and
# are left for hand population — see category_tree.py's own docstring.
#
# Output: db/db_category_words.py — {node_path_tuple: [word,...]}.
#
# Run as a module so package imports resolve: python3 -m tools.expand_category

from nltk.corpus import wordnet as wn
from questionnaire.category_tree import CATEGORY_TREE
from lexicon_db.db_lexicon import LEXICON

MAX_HYPONYM_DEPTH = 6

# path[1] (the subtype right under the top-level type) -> the set of
# db_lexicon.py `category` values expected for a real member of that
# branch. Branches not listed here skip the category cross-check and
# rely on lexicon-key membership alone.
SUBTYPE_LEXICON_CATEGORIES = {
    "animal":   {"animal"},
    "person":   {"person"},
    "plant":    {"plant", "food"},
    "everyday": {"object"},
    "weapon":   {"object"},
    "food":     {"food"},
    "place":    {"place", "group"},
    "weather":  {"weather"},
    "emotion":  {"emotion", "state"},
    "death_loss": {"event", "state"},
}

_LEXICON_KEYS = set(LEXICON.keys())


def hyponym_closure(synset, max_depth: int = MAX_HYPONYM_DEPTH):
    """All hyponyms of `synset`, recursively, up to max_depth levels
    down (stops naturally once a branch has no more hyponyms)."""
    seen = set()
    frontier = [synset]
    depth = 0
    while frontier and depth < max_depth:
        next_frontier = []
        for s in frontier:
            for h in s.hyponyms():
                if h not in seen:
                    seen.add(h)
                    next_frontier.append(h)
        frontier = next_frontier
        depth += 1
    return seen


def expand_anchor(anchor_name: str, allowed_categories=None):
    """Returns the sorted list of common words (already a top-level key
    in db/db_lexicon.py, and — if `allowed_categories` is given —
    independently classified under one of those categories) found among
    `anchor_name` and all of its hyponyms."""
    try:
        synset = wn.synset(anchor_name)
    except Exception:
        return []

    synsets = {synset} | hyponym_closure(synset)
    words = set()
    for s in synsets:
        for lemma in s.lemmas():
            w = lemma.name().lower()
            if w not in _LEXICON_KEYS:
                continue
            if allowed_categories and LEXICON[w]["category"] not in allowed_categories:
                continue
            words.add(w)
    return sorted(words)


def walk_anchored(tree: dict = CATEGORY_TREE, path=()):
    """Yields (path, node) for every node — leaf OR intermediate, at any
    depth — that has a non-None wordnet_anchor."""
    for key, node in tree.items():
        if not isinstance(node, dict):
            continue
        new_path = path + (key,)
        if node.get("wordnet_anchor"):
            yield new_path, node
        if "facets" in node:
            yield from walk_anchored(node["facets"], new_path)
        elif any(isinstance(v, dict) for v in node.values()):
            yield from walk_anchored(node, new_path)


def build_category_words():
    resolved = {}
    for path, node in walk_anchored():
        subtype = path[1] if len(path) > 1 else None
        allowed = SUBTYPE_LEXICON_CATEGORIES.get(subtype)
        resolved[path] = expand_anchor(node["wordnet_anchor"], allowed)
    return resolved


if __name__ == "__main__":
    resolved = build_category_words()
    empty = {p: w for p, w in resolved.items() if not w}
    total_words = sum(len(w) for w in resolved.values())

    with open("lexicon_db/db_category_words.py", "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("db_category_words.py\n")
        f.write("Automatically generated by tools/expand_category.py\n")
        f.write("Maps each anchored node of character/category_tree.py (leaf or\n")
        f.write("intermediate) to its real member words, expanded via\n")
        f.write("WordNet hyponyms, filtered against db/db_lexicon.py and\n")
        f.write("against each word's own category in that lexicon.\n")
        f.write("Nodes without a wordnet_anchor do not appear here — they are filled in by hand.\n")
        f.write('"""\n\n')
        f.write("CATEGORY_WORDS = {\n")
        for path, words in resolved.items():
            f.write(f"    {path!r}: {words!r},\n")
        f.write("}\n")

    print(f"Anchored nodes expanded: {len(resolved)}")
    print(f"Total words assigned: {total_words}")
    print(f"Nodes with an anchor but 0 words found ({len(empty)}):")
    for p in empty:
        print(f"   {p}")
