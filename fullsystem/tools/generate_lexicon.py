# tools/generate_lexicon.py — UNIQUE HOST
#
# Builds db/db_lexicon.py: the N most common English words, each tagged
# with its WordNet "lexicographer file" (lexname) — a ready-made,
# linguist-built taxonomy of 25 noun categories (noun.animal, noun.person,
# noun.artifact, noun.food, noun.location, noun.feeling, noun.phenomenon,
# noun.body, noun.plant, noun.substance, etc.) plus verbs/adjectives by
# POS. This replaces the earlier hand-rolled CATEGORY_ROOTS classifier —
# WordNet's own lexname already IS the level-1 taxonomy, no need to
# reinvent it.
#
# Level 2+ subcategories (herbivore/carnivore, domestic/wild, etc.) are
# still hand-anchored per category via specific synsets + hyponym
# expansion — see tools/expand_category.py (built per-category as the
# world/likes question trees are defined, one topic at a time).
#
# NO sentiment/axis values are assigned here — those come later from the
# questionnaire's "world/likes" tree (a category-level answer bulk-fills
# its member words; a specific word can later be overridden individually).
#
# node_type ends up with exactly 4 possible values -- biological,
# non_biological, action, quality -- used as the
# top-level Subject/Object/Sensorial/Structural split used to feed a
# sentence: biological=Subject (North), non_biological=Object (South),
# action=Sensorial (verb/movement), quality=Structural (adjective).
#
# POS SOURCE — fixed: uses each word's DOMINANT part of
# speech measured over the real Brown corpus (dominant_pos, same
# approach as tools/generate_axis_lexicon.py), not a single isolated
# word run through pos_tag. Two bugs this fixes:
#   1. classify_word used to try a WordNet NOUN sense for every word
#      first, regardless of its real usage -- so a verb/adjective that
#      also happened to have some obscure noun sense got silently
#      misclassified as that noun's category. E.g. "have"/"was"/"be"/
#      "are" landed as biological/non_biological because their first
#      WordNet noun sense is "a person of wealth" / a US state
#      homograph / the element beryllium / the area unit "are" --
#      total noise, nothing to do with the word's real usage.
#   2. Even after checking the word's own tag first, tagging a SINGLE
#      word with no sentence context (pos_tag([word])) still guesses
#      wrong for common ambiguous words -- "walk"/"run"/"jump"/"swim"/
#      "fly"/"cold"/"red" all got tagged NN/JJ-wrong in isolation, even
#      though their dominant real-corpus usage is VERB/ADJ. Measuring
#      the tag distribution across actual Brown corpus sentences (this
#      file's dominant_pos) fixes this the same way it already fixed
#      tools/generate_axis_lexicon.py's verb/adjective split.
#
# Run once: python3 tools/generate_lexicon.py
# Regenerate any time the word count changes.

import json
import nltk
from collections import Counter, defaultdict
from wordfreq import top_n_list

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
nltk.download("brown", quiet=True)
nltk.download("universal_tagset", quiet=True)
from nltk.corpus import wordnet as wn
from nltk.corpus import brown

N_WORDS = 6000

# Universal-tagset categories to exclude entirely (articles, pronouns,
# prepositions, conjunctions, numbers, particles, punctuation/other) —
# not evaluable concepts; these live hand-authored elsewhere
# (pronouns in core/response_matrix.py SOCIAL_POSITIONING).
FUNCTION_POS = {"DET", "ADP", "CONJ", "PRON", "NUM", "PRT", "X", "."}

# Modals map to VERB in the universal tagset, but they're not
# conjugable action words -- they already live hand-authored, with
# their real forms, in db/db_axis_lexicon.py (same skip-list as
# tools/generate_axis_lexicon.py's skip_modals).
SKIP_MODALS = {
    "will", "would", "can", "could", "may", "might", "shall",
    "should", "must", "ought",
}

# WordNet lexname -> UNIQUE HOST top-level category label + biological flag
LEXNAME_MAP = {
    "noun.animal":       ("animal", True),
    "noun.plant":        ("plant", True),
    "noun.person":       ("person", True),
    "noun.body":         ("body_part", True),
    "noun.food":         ("food", False),
    "noun.artifact":     ("object", False),
    "noun.object":       ("object", False),
    "noun.location":     ("place", False),
    "noun.phenomenon":   ("weather", False),
    "noun.feeling":      ("emotion", False),
    "noun.substance":    ("substance", False),
    "noun.group":        ("group", False),
    "noun.possession":   ("possession", False),
    "noun.act":          ("act", False),
    "noun.event":        ("event", False),
    "noun.state":        ("state", False),
    "noun.cognition":    ("cognition", False),
    "noun.communication":("communication", False),
    "noun.attribute":    ("attribute", False),
    "noun.time":         ("time", False),
    "noun.quantity":     ("quantity", False),
    "noun.relation":     ("relation", False),
    "noun.shape":        ("shape", False),
    "noun.process":      ("process", False),
    "noun.motive":       ("motive", False),
    "noun.Tops":         ("abstract", False),
}


# Manual overrides — WordNet's own taxonomy correctly (biologically)
# files these under noun.animal, but for UNIQUE HOST's purposes they
# should read as "person", not "animal". Extend this list as more
# mismatches turn up; it's meant to stay small.
CATEGORY_OVERRIDES = {
    "human":   "person",
    "humans":  "person",
    "female":  "person",
    "females": "person",
    "male":    "person",
    "males":   "person",
    "man":     "person",
    "woman":   "person",
    "men":     "person",
    "women":   "person",
}


# ── ROLEPLAY VOCABULARY ────────────────────────────────────
# wordfreq's top_n_list ranks by GENERAL English usage frequency —
# genre-specific words like "bandit" or "dungeon" don't make the top
# N_WORDS cut even though they're common in the kind of scenes UNIQUE
# HOST characters actually get used in (: "bandit"
# didn't resolve to anything at all). Bumping N_WORDS to catch them
# would also pull in a lot of unrelated common words and re-run the
# full Brown-corpus tagging pass for no reason — instead, classify this
# curated list directly with the SAME classify_word used for
# everything else, so it stays consistent with the rest of the lexicon
# rather than being a separate hand-rolled table. Skips dominant_pos
# (these are all nouns; several barely appear in the 1961 Brown corpus
# at all, so measuring their real-corpus tag distribution isn't
# reliable the way it is for common words) and classifies with
# tag="NOUN" directly -- WordNet's own lexname split still does the
# real categorization work.
ROLEPLAY_WORDS = [
    # people
    "bandit", "villain", "thief", "rogue", "mercenary", "assassin",
    "outlaw", "highwayman", "sorcerer", "warlock", "blacksmith",
    "innkeeper", "scoundrel", "swindler", "raider", "pirate",
    "smuggler", "nomad", "cutthroat", "brigand", "adventurer",
    "mercenary", "bounty hunter", "vagrant",
    # places / objects
    "dungeon", "tavern", "castle", "fortress", "cave", "ambush",
    "loot", "coin",
]

# ── FANTASY ROLEPLAY VOCABULARY ────────────────────────────
# Same problem as ROLEPLAY_WORDS above, narrower genre: high-fantasy
# creatures/objects ("wizard", "goblin", "amulet"...) barely register in
# general-English frequency lists, so they never made the top N_WORDS cut
# either. Classified with the SAME classify_word pipeline, tag="NOUN"
# forced for the same reason (these barely appear in the 1961 Brown
# corpus, so dominant_pos isn't reliable for them). Kept as its own
# list (not merged into ROLEPLAY_WORDS) so it's easy to find/extend later
# without touching the more general roleplay list above.
#
# Deliberately NOT given a fixed universal push in db/db_concepts.py —
# per character/questionnaire.py's WORLD_GROUPS pattern (confirmed
# ), these get a per-character push via a new "fantasy_opinion"
# question instead, same as ghost/shadow/corpse under "supernatural_opinion".
FANTASY_WORDS = [
    # people / creatures
    "wizard", "witch", "sorceress", "necromancer", "paladin", "mage",
    "druid", "shaman", "oracle", "alchemist", "elf", "dwarf", "orc",
    "goblin", "troll", "ogre", "giant", "hobbit", "gnome", "imp",
    "fairy", "banshee", "wraith", "vampire", "werewolf", "zombie",
    "skeleton", "phoenix", "griffin", "chimera", "basilisk", "hydra",
    "demon",
    # objects / places / abstractions
    "potion", "wand", "rune", "amulet", "scroll", "tome", "relic",
    "artifact", "sigil", "portal", "throne", "crypt", "curse",
    "ritual", "prophecy", "armor",
]


def _build_brown_counts():
    """Word -> Counter(universal POS tag -> count), measured over every
    sentence in the Brown corpus (same approach as
    tools/generate_axis_lexicon.py's dominant_pos())."""
    tagged = brown.tagged_words(tagset="universal")
    counts = defaultdict(Counter)
    for word, tag in tagged:
        counts[word.lower()][tag] += 1
    return counts


def dominant_pos(word: str, brown_counts: dict):
    """Real dominant part of speech for `word`, measured over the Brown
    corpus. Returns None if the word never appears in it."""
    counts = brown_counts.get(word)
    return counts.most_common(1)[0][0] if counts else None


def classify_word(word: str, tag: str):
    """Returns (category, node_type, synonyms) using the word's own
    DOMINANT part of speech (Brown-corpus-measured, see dominant_pos())
    FIRST -- verb -> action, adjective -> quality -- and only falling
    back to WordNet's noun lexname taxonomy when the word's dominant
    usage is actually a noun. Fixed 2026-09-05, see module docstring.
    """
    if word in CATEGORY_OVERRIDES:
        category = CATEGORY_OVERRIDES[word]
        synsets = wn.synsets(word, pos=wn.NOUN)
        synonyms = sorted({l.name().replace("_", " ") for l in synsets[0].lemmas()}) if synsets else []
        return category, "biological", synonyms[:6]

    if tag == "VERB":
        return "action", "action", []
    if tag == "ADJ":
        return "quality", "quality", []
    if tag == "NOUN":
        synsets = wn.synsets(word, pos=wn.NOUN)
        if synsets:
            lexname = synsets[0].lexname()
            category, is_bio = LEXNAME_MAP.get(lexname, ("abstract", False))
            node_type = "biological" if is_bio else "non_biological"
            synonyms = sorted({l.name().replace("_", " ") for l in synsets[0].lemmas()})
            return category, node_type, synonyms[:6]
    return None, None, []


def build_lexicon(n_words: int = N_WORDS) -> dict:
    words = top_n_list("en", n_words)
    brown_counts = _build_brown_counts()
    lexicon = {}

    for word in words:
        if not word.isalpha() or len(word) < 2:
            continue
        if word in SKIP_MODALS:
            continue  # already hand-authored in db/db_axis_lexicon.py

        tag = dominant_pos(word, brown_counts)
        if tag is None or tag in FUNCTION_POS:
            continue  # never seen in Brown, or a grammatical function word

        category, node_type, synonyms = classify_word(word, tag)
        if category is None:
            continue  # dominant usage is ADV/other -- not one of the 4 categories

        lexicon[word] = {
            "category": category,
            "node_type": node_type,
            "synonyms": synonyms,
        }

    for word in ROLEPLAY_WORDS:
        if word in lexicon:
            continue
        category, node_type, synonyms = classify_word(word, "NOUN")
        if category is None:
            continue
        lexicon[word] = {
            "category": category,
            "node_type": node_type,
            "synonyms": synonyms,
        }

    for word in FANTASY_WORDS:
        if word in lexicon:
            continue
        category, node_type, synonyms = classify_word(word, "NOUN")
        if category is None:
            continue
        lexicon[word] = {
            "category": category,
            "node_type": node_type,
            "synonyms": synonyms,
        }

    return lexicon


if __name__ == "__main__":
    lex = build_lexicon()

    counts = {}
    for entry in lex.values():
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    print("Category counts:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} {n}")

    with open("db/db_lexicon.py", "w", encoding="utf-8") as f:
        f.write("# db/db_lexicon.py — UNIQUE HOST\n")
        f.write("# AUTO-GENERATED by tools/generate_lexicon.py — do not hand-edit.\n")
        f.write("# Word -> {category, node_type, subtype, synonyms}. NO axis values here —\n")
        f.write("# those are filled per-category (bulk) or per-word (override) by the\n")
        f.write("# questionnaire's world/likes tree at character-creation time.\n\n")
        f.write("LEXICON = ")
        json_text = json.dumps(lex, indent=2, ensure_ascii=False)
        # json -> valid Python literal (null/true/false -> None/True/False)
        json_text = json_text.replace(": null", ": None").replace(": true", ": True").replace(": false", ": False")
        f.write(json_text)
        f.write("\n")

    print(f"\nWrote db/db_lexicon.py with {len(lex)} words.")
