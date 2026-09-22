"""
generate_subject_lexicon.py
-------------------------------------------------------------------------
Generates the lexicon of FIXED SUBJECTS (fixed-value nouns, distinct from
the pronouns/dynamic subjects of db_axis_lexicon.py): common domestic
animals, family members, and generic person roles.

These are the nouns that remain EXCLUDED from the per-axis lexicon
(db_axis_lexicon_generated.py only took verbs and adjectives) — this is where
they really live, grouped by category with their real synonyms via
WordNet, not just the base word.

Output: db_subject_lexicon.py
-------------------------------------------------------------------------
"""

from nltk.corpus import wordnet as wn


ANIMAL_ROOT = wn.synset("animal.n.01")


def is_animal_synset(syn):
    """True if the synset (or any of its hypernyms) is 'animal'."""
    for path in syn.hypernym_paths():
        if ANIMAL_ROOT in path:
            return True
    return False


def synonyms_for(word, pos="n", max_synsets=2, require_animal=False):
    """Real synonyms of a word (first senses, the most common).
    Filters proper names (composers, acronyms, etc.) and rare entries.
    If require_animal=True, ignores senses that are not from the animal kingdom
    (e.g. 'turtle' = sweater, 'whale' = big person) and looks for the first
    real animal sense, regardless of which position it is in."""
    seen = []
    synsets = wn.synsets(word, pos=pos)
    if require_animal:
        synsets = [s for s in synsets if is_animal_synset(s)] or synsets
    for syn in synsets[:max_synsets]:
        for lemma in syn.lemma_names():
            name = lemma.replace("_", " ")
            # discard proper names (2+ capitalized words, or an acronym like "MD")
            words_in_name = name.split()
            has_inner_capital = any(
                tok[0].isupper() for i, tok in enumerate(words_in_name) if i > 0
            )
            is_all_caps_short = name.isupper() and len(name) <= 3
            # discard lone capitalized terms (religious/proper
            # senses like "Word"/"Logos"), except abbreviations like "Dr."
            is_capitalized_word = (
                len(words_in_name) == 1
                and name[0].isupper()
                and not name.endswith(".")
            )
            if has_inner_capital or is_all_caps_short or is_capitalized_word:
                continue
            if name.lower() not in [s.lower() for s in seen]:
                seen.append(name)
    return seen if seen else [word]


# =============================================================================
# DOMESTIC / MOST COMMONLY USED ANIMALS
# =============================================================================
ANIMALS_CORE = [
    "dog", "cat", "horse", "bird", "fish", "rabbit", "hamster",
    "mouse", "rat", "snake", "turtle", "lizard", "frog", "pig",
    "cow", "goat", "sheep", "chicken", "duck", "wolf", "fox",
    "bear", "lion", "tiger", "elephant", "monkey", "deer", "owl",
    "eagle", "shark", "whale", "dolphin", "spider", "bee", "ant",
    "butterfly", "cattle",
    # added after cross-checking with the 10k most common words (wordfreq + WordNet)
    "turkey", "cricket", "jay", "robin", "bull", "bass", "ram",
    "buffalo", "fly", "insect", "lamb", "buck", "salmon", "puppy",
    "kitten", "drake", "crane", "cardinal", "cod", "cub", "bunny",
    "doe", "goose", "swan", "livestock", "hawk", "pony", "crow",
    "shrimp", "python", "trout", "worm", "pet", "beast",
]

# =============================================================================
# FAMILY — members and roles
# =============================================================================
FAMILY_CORE = [
    "father", "mother", "dad", "mom", "grandfather", "grandmother",
    "grandpa", "grandma", "son", "daughter", "brother", "sister",
    "uncle", "aunt", "cousin", "nephew", "niece", "husband", "wife",
    "spouse", "stepfather", "stepmother", "stepbrother", "stepsister",
    "godfather", "godmother", "twin", "sibling", "parent", "child",
    "baby", "infant", "toddler", "grandchild", "grandson",
    "granddaughter", "in-law", "widow", "widower", "orphan",
    # added after cross-checking with the 10k most common words (wordfreq + WordNet)
    "grandparent", "grandchildren", "ancestor", "descendant", "heir",
    "bride", "groom", "fiance", "fiancee", "boyfriend", "girlfriend",
    "relative", "kin",
]

# =============================================================================
# GENERIC PERSON ROLES (non-family, not relationship-dynamic)
# =============================================================================
PEOPLE_ROLES_CORE = [
    "man", "woman", "boy", "girl", "person", "child", "adult",
    "teenager", "elder", "neighbor", "stranger", "coworker",
    "colleague", "boss", "employee", "teacher", "doctor", "nurse",
    "police officer", "soldier", "priest", "judge", "lawyer",
    "farmer", "worker", "servant", "master", "owner", "tenant",
    "customer", "guest", "host", "visitor", "passenger", "driver",
]


def build_category(word_list, pos="n", max_synsets=2, require_animal=False):
    result = {}
    for w in word_list:
        lookup = w.replace(" ", "_")
        result[w] = synonyms_for(
            lookup, pos=pos, max_synsets=max_synsets, require_animal=require_animal
        )
    return result


def main():
    animals = build_category(ANIMALS_CORE, max_synsets=1, require_animal=True)
    family = build_category(FAMILY_CORE, max_synsets=2)
    people = build_category(PEOPLE_ROLES_CORE, max_synsets=2)

    with open("db_subject_lexicon.py", "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("db_subject_lexicon.py\n")
        f.write("Automatically generated by generate_subject_lexicon.py\n")
        f.write("FIXED subjects (nouns): animals, family, person roles.\n")
        f.write("Real synonyms extracted from WordNet (first 2 senses per word).\n")
        f.write("Different from DYNAMIC_SUBJECTS in db_axis_lexicon.py (friend/enemy/hero/\n")
        f.write("etc., which DO depend on the character's relationship).\n")
        f.write('"""\n\n')

        f.write("# Domestic / most commonly used animals, with synonyms\n")
        f.write("SUBJECTS_ANIMALS = {\n")
        for k, v in animals.items():
            f.write(f"    {k!r}: {v!r},\n")
        f.write("}\n\n")

        f.write("# Family -- members and roles, with synonyms\n")
        f.write("SUBJECTS_FAMILY = {\n")
        for k, v in family.items():
            f.write(f"    {k!r}: {v!r},\n")
        f.write("}\n\n")

        f.write("# Generic person roles (non-family, not relationship-dynamic)\n")
        f.write("SUBJECTS_PEOPLE_ROLES = {\n")
        for k, v in people.items():
            f.write(f"    {k!r}: {v!r},\n")
        f.write("}\n")

    print(f"Animales: {len(animals)}")
    print(f"Familia: {len(family)}")
    print(f"Roles de persona: {len(people)}")
    print("File generated: db_subject_lexicon.py")


if __name__ == "__main__":
    main()
