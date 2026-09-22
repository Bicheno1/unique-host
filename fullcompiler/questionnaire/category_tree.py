# character/category_tree.py — UNIQUE HOST
#
# CATEGORY TREE — the "world/likes" questionnaire structure.
#
# Restructured to match the 4 node types confirmed from the
# lexicon fix ( of the state doc, db/db_lexicon.py's `node_type`):
# biological, non_biological, quality, action. These are the 4 pyramid
# tips — every concept in the system is one of these 4 at the root:
#
#   type (top: biological | non_biological | quality | action)
#     |__ subtype (e.g. "animal")
#           |__ facet (a grouping dimension, e.g. "diet")
#                 |__ leaf options (horizontal siblings, mutually exclusive
#                     within their facet, e.g. "herbivore" / "carnivore")
#                       |__ (optional) further sub-facets, same pattern
#
# A facet's leaves are "horizontal siblings": each gets its own 1-10
# question, and answering one does NOT set the others — they are
# independent alternatives that the questionnaire may ask about
# separately (e.g. "how much do herbivores appeal to them?" AND
# "how much do carnivores appeal to them?" can both be asked).
#
# Previously this used the original CCM v1 6-type schema (subject/
# object/environment/status/action/illogical, still what's hardcoded in
# the older db/db_concepts.py). Migration: subject -> biological;
# object + environment merged into non_biological (both are
# non-biological, no reason to keep them as separate pyramids); action
# unchanged; illogical/supernatural folded into non_biological (matches
# how "ghost" etc. actually landed in the lexicon fix) pending a
# clearer home if that turns out wrong.
#
# POLYHIERARCHY — TRIED, THEN RETIRED: status/emotion was
# briefly modeled as a node with two parents (biological AND quality),
# since geometrically emotion concepts sit at the seam where quality's
# own East/West sub-trees converge. Superseded same day: emotion isn't
# a THING to classify in a tree of nouns at all -- it's a LABEL for the
# character's own reaction (where their centroid ends up after a
# concept's push), which the engine already computes dynamically. See
# systems/chemical_system.py's MATRIX_MODES, now with an "emotion" field
# per (category, axis) cell (anger/fear/joy/trust/etc, one of 16, each
# grounded in that cell's own "ref" neurochemical signature) -- e.g.
# fear = (danger, Lv), the same cell as the "flee" behavior, no separate
# tree node needed. category_tree.py only classifies THINGS (animal,
# person, object, action) from here on.
#
# `wordnet_anchor` (when present) is the synset used to expand this
# node's leaf into member words via hyponyms — see
# tools/expand_category.py (TODO: build once tree is confirmed).
# Nodes without a wordnet_anchor have no clean WordNet equivalent and
# must be populated by hand.
#
# `quality` (adjectives) is new as an explicit top-level type here --
# its real East/West (raw perception vs. relational judgment) split
# still lives in db/db_axis_lexicon.py and hasn't been merged into this
# tree's facet structure yet. It's listed here mainly so EMOTION/
# DEATH_LOSS have a real second parent to attach to; populating
# quality's own subtypes/facets is separate future work.
#
# TODO: this is a first full pass over all topics.
# Depth/leaves are a reasonable draft — expected to be trimmed or
# extended once reviewed.


CATEGORY_TREE = {

    # ==================================================================
    "biological": {

        # "body_part" subtypes from the new lexicon -- same pattern,
        #  "misc" (5 words) is left out, no clear theme.
        "limb_or_face": {"lexicon_subtype": "external", "lexicon_category": "body_part"},
        "internal_organ": {"lexicon_subtype": "internal", "lexicon_category": "body_part"},
        "bodily_fluid":  {"lexicon_subtype": "fluid",    "lexicon_category": "body_part"},
        "genital":       {"lexicon_subtype": "genital",  "lexicon_category": "body_part"},

        "animal": {
            "wordnet_anchor": "animal.n.01",
            "facets": {
                "diet": {
                    "herbivore": {"wordnet_anchor": "herbivore.n.01"},
                    "carnivore": {"wordnet_anchor": "carnivore.n.01"},
                    "omnivore":  {"wordnet_anchor": None},
                },
                "domestication": {
                    "domestic": {"wordnet_anchor": "domestic_animal.n.01"},
                    "wild":     {"wordnet_anchor": None},
                },
                "size": {
                    "large": {"wordnet_anchor": None},
                    "small": {"wordnet_anchor": None},
                },
                "biology": {
                    "mammal":  {"wordnet_anchor": "mammal.n.01"},
                    "reptile": {"wordnet_anchor": "reptile.n.01"},
                    "bird":    {"wordnet_anchor": "bird.n.01"},
                    "fish":    {"wordnet_anchor": "fish.n.01"},
                    "insect":  {"wordnet_anchor": "insect.n.01"},
                },
                "habitat": {
                    "aquatic":    {"wordnet_anchor": None},
                    "terrestrial":{"wordnet_anchor": None},
                    "aerial":     {"wordnet_anchor": None},
                },
            },
        },

        "person": {
            "wordnet_anchor": "person.n.01",
            "facets": {
                "relation": {
                    "family":     {"wordnet_anchor": None},
                    "friend":     {"wordnet_anchor": None},
                    "stranger":   {"wordnet_anchor": None},
                    "authority":  {"wordnet_anchor": None},
                },
                "attractiveness": {
                    "attractive": {"wordnet_anchor": None},
                    "unattractive": {"wordnet_anchor": None},
                },
                "temperament": {
                    "kind":     {"wordnet_anchor": None},
                    "hostile":  {"wordnet_anchor": None},
                },
                "physical_strength": {
                    "strong": {"wordnet_anchor": None},
                    "weak":   {"wordnet_anchor": None},
                },
                "appearance_descriptive": {
                    "color": {"wordnet_anchor": None, "descriptive_only": True},
                    "build": {"wordnet_anchor": None, "descriptive_only": True},
                },
            },
        },

        "plant": {
            "wordnet_anchor": "plant.n.02",
            "facets": {
                "edibility": {
                    "edible": {"wordnet_anchor": "edible_fruit.n.01"},
                    "toxic":  {"wordnet_anchor": "poisonous_plant.n.01"},
                },
                "rarity": {
                    "common": {"wordnet_anchor": None},
                    "rare":   {"wordnet_anchor": None},
                },
            },
        },
    },

    # ==================================================================
    # Merged from the old "object" + "environment" (both non-biological,
    # no reason to split them into separate pyramids) + "illogical"
    # (supernatural landed non_biological in the lexicon fix).
    "non_biological": {

        "everyday": {
            "wordnet_anchor": "artifact.n.01",
            "facets": {
                "kind": {
                    "clothing":  {"wordnet_anchor": "clothing.n.01"},
                    "hygiene":   {"wordnet_anchor": "toiletry.n.01"},
                    "furniture": {"wordnet_anchor": "furniture.n.01"},
                    "tool":      {"wordnet_anchor": "tool.n.01"},
                    "technology":{"wordnet_anchor": "electronic_equipment.n.01"},
                },
                "utility": {
                    "useful":  {"wordnet_anchor": None},
                    "useless": {"wordnet_anchor": None},
                },
                "complexity": {
                    "simple":  {"wordnet_anchor": None},
                    "complex": {"wordnet_anchor": None},
                },
            },
        },

        "weapon": {
            "wordnet_anchor": "weapon.n.01",
            "facets": {
                "range": {
                    "melee":  {"wordnet_anchor": "edge_tool.n.01"},
                    "ranged": {"wordnet_anchor": "projectile.n.01"},
                },
                "scale": {
                    "small":       {"wordnet_anchor": None},
                    "destructive": {"wordnet_anchor": None},
                },
            },
        },

        "food": {
            "wordnet_anchor": "food.n.01",
            "facets": {
                "familiarity": {
                    "familiar": {"wordnet_anchor": None},
                    "novel":    {"wordnet_anchor": None},
                },
            },
        },

        "place": {
            "wordnet_anchor": "location.n.01",
            "facets": {
                "setting": {
                    "urban":   {"wordnet_anchor": None},
                    "natural": {"wordnet_anchor": None},
                },
                "safety": {
                    "safe":       {"wordnet_anchor": None},
                    "dangerous":  {"wordnet_anchor": None},
                },
                "familiarity": {
                    "known":    {"wordnet_anchor": None},
                    "unknown":  {"wordnet_anchor": None},
                },
            },
        },

        "weather": {
            "wordnet_anchor": "natural_phenomenon.n.01",
            "facets": {
                "kind": {
                    "rain":       {"wordnet_anchor": None},
                    "wind":       {"wordnet_anchor": None},
                    "storm":      {"wordnet_anchor": None},
                    "earthquake": {"wordnet_anchor": None},
                },
                "intensity": {
                    "mild":    {"wordnet_anchor": None},
                    "extreme": {"wordnet_anchor": None},
                },
            },
        },

        # No WordNet equivalent — CCM-specific, populated by hand.
        # Folded in from the old "illogical" top-level type; revisit if
        # supernatural turns out to need its own seam like emotion does.
        "supernatural": {
            "wordnet_anchor": None,
            "facets": {
                "reaction": {
                    "fear":        {"wordnet_anchor": None},
                    "fascination": {"wordnet_anchor": None},
                },
            },
        },

        # "object"/"place" subtypes from the new lexicon,
        # same lexicon_subtype pattern as quality/action (no
        # wordnet_anchor, grouped directly by the subtype each word
        # already carries). "misc" (299 object + 5 body_part) is left
        # out on purpose: no common theme, it doesn't make a useful question.
        "vehicle":     {"lexicon_subtype": "vehicle",     "lexicon_category": "object"},
        "clothing":    {"lexicon_subtype": "clothing",    "lexicon_category": "object"},
        "mechanism":   {"lexicon_subtype": "mechanism",   "lexicon_category": "object"},
        "container":   {"lexicon_subtype": "container",   "lexicon_category": "object"},
        "furniture_pieces": {"lexicon_subtype": "furniture", "lexicon_category": "object"},
        "drug":        {"lexicon_subtype": "drug",        "lexicon_category": "object"},
        "handheld_tool": {"lexicon_subtype": "tool", "lexicon_category": "object"},
        "celestial":   {"lexicon_subtype": "celestial",   "lexicon_category": "object"},
        "instrument":  {"lexicon_subtype": "music",       "lexicon_category": "object"},
        "electronics": {"lexicon_subtype": "electronics", "lexicon_category": "object"},
        "building":    {"lexicon_subtype": "building",    "lexicon_category": "place"},
        "landform":    {"lexicon_subtype": "landform",    "lexicon_category": "place"},
    },

    # ==================================================================
    # NOTE: "quality" (adjectives) was added here only to
    # give emotion/death_loss a second parent for the polyhierarchy
    # experiment — since that's retired (see note above MATRIX_MODES'
    # "emotion" field is where emotion actually lives now), there's
    # nothing to put here yet. Real East/West (raw perception vs.
    # relational judgment) structure for adjectives still lives in
    # db/db_axis_lexicon.py, unmerged. Add "quality": {...} back here
    # once that gets folded into this tree's facet structure.

    # ==================================================================
    # QUALITY (adjectives) -- added together with the new
    # lexicon (~8974 words). Unlike biological/non_biological, these
    # subtypes do NOT come from a wordnet_anchor/hyponym -- they come
    # straight from the `subtype` field each word already carries in
    # lexicon_db/db_lexicon.py (hand-classified in the new lexicon,
    # see quality_categories.py from the chat that built it). That is
    # why each one is a direct LEAF (no intermediate facets) and is
    # populated with tools/expand_category_by_subtype.py, not with
    # expand_category.py.
    "quality": {
        "relational":  {"lexicon_subtype": "relational"},
        "physical":    {"lexicon_subtype": "physical"},
        "evaluative":  {"lexicon_subtype": "evaluative"},
        "quantity":    {"lexicon_subtype": "quantity"},
        "temporal":    {"lexicon_subtype": "temporal"},
        "personality": {"lexicon_subtype": "personality"},
        "certainty":   {"lexicon_subtype": "certainty"},
        "emotional":   {"lexicon_subtype": "emotional"},
        "importance":  {"lexicon_subtype": "importance"},
        "comparative": {"lexicon_subtype": "comparative"},
        "sensory":     {"lexicon_subtype": "sensory"},
        "cognitive":   {"lexicon_subtype": "cognitive"},
        "social":      {"lexicon_subtype": "social"},
        "aesthetic":   {"lexicon_subtype": "aesthetic"},
        "difficulty":  {"lexicon_subtype": "difficulty"},
        "speed":       {"lexicon_subtype": "speed"},
        "economic":    {"lexicon_subtype": "economic"},
    },

    # ==================================================================
    "action": {

        "physical_contact": {
            "wordnet_anchor": None,
            "facets": {
                "expectation": {
                    "expected":   {"wordnet_anchor": None},
                    "unexpected": {"wordnet_anchor": None},
                },
            },
        },

        "conflict": {
            "wordnet_anchor": None,
            "facets": {
                "kind": {
                    "verbal":   {"wordnet_anchor": None},
                    "physical": {"wordnet_anchor": None},
                },
                "onset": {
                    "sudden":      {"wordnet_anchor": None},
                    "anticipated": {"wordnet_anchor": None},
                },
            },
        },

        "authority_rules": {
            "wordnet_anchor": None,
            "facets": {
                "stance": {
                    "obedient": {"wordnet_anchor": None},
                    "rebellious": {"wordnet_anchor": None},
                },
                "novelty": {
                    "familiar_rule": {"wordnet_anchor": None},
                    "new_rule":      {"wordnet_anchor": None},
                },
            },
        },

        # Same as "quality" above: subtypes straight by lexicon_subtype,
        # no wordnet_anchor.
        "communication": {"lexicon_subtype": "communication"},
        "social":        {"lexicon_subtype": "social", "_note": "social verbs -- careful, same name as quality.social but they are different branches (path[0] separates them)"},
        "change":        {"lexicon_subtype": "change"},
        "motion":        {"lexicon_subtype": "motion"},
        "contact":       {"lexicon_subtype": "contact", "_note": "physical contact verbs -- different from physical_contact above (that one is an old CCM facet with its own facets; this one comes straight from the lexicon subtype)"},
        "stative":       {"lexicon_subtype": "stative"},
        "cognition":     {"lexicon_subtype": "cognition"},
        "possession":    {"lexicon_subtype": "possession"},
        "perception":    {"lexicon_subtype": "perception"},
        "creation":      {"lexicon_subtype": "creation"},
        "emotion_verbs": {"lexicon_subtype": "emotion", "_note": "verbs (feel/love/fear...); the key cannot be plain 'emotion' because of the polyhierarchy attempt removed above"},
        "competition":   {"lexicon_subtype": "competition"},
        "consumption":   {"lexicon_subtype": "consumption"},
        "body":          {"lexicon_subtype": "body"},
    },
}


def walk_leaves(tree: dict = CATEGORY_TREE, path=()):
    """Yields (path_tuple, node_dict) for every leaf option in the tree
    (nodes with no further 'facets' key beneath them). A polyhierarchy
    node (e.g. emotion, death_loss) is visited once PER PARENT PATH,
    same underlying dict each time — same as walking a DAG through
    multiple hypernym chains in WordNet."""
    for key, node in tree.items():
        new_path = path + (key,)
        if isinstance(node, dict) and "facets" in node:
            yield from walk_leaves(node["facets"], new_path)
        elif isinstance(node, dict) and any(isinstance(v, dict) for v in node.values()) and "wordnet_anchor" not in node:
            yield from walk_leaves(node, new_path)
        else:
            yield new_path, node
