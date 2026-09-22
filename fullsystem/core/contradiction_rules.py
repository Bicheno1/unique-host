# core/contradiction_rules.py — UNIQUE HOST
#
# "ONLY WHAT IS CLEARLY IMPOSSIBLE" CONTRADICTION RULE.
#
# PROBLEM IT SOLVES
# ─────────────────────
# detect_contradiction used to be a WHITELIST: a subject could only do
# the verbs hand-written in its `related` (or the 4 in IMPLICIT_
# CAPABILITIES: walk/run/hide/breathe). With a lexicon of ~9000 words and
# ~2000 verbs entering with an empty `related`, almost any normal verb
# ("raises", "speaks", "sells", "steals"...) was flagged as a contradiction.
# Measured: 9/20 normal roleplay sentences flagged; and the contradiction
# REPLACES the normal response, so it showed up in almost half of the
# turns. A whitelist fails at scale: you have to enumerate everything possible.
#
# WHAT IS NEW: BLACKLIST
# ─────────────────────
# By default NOTHING is a contradiction. A (subject, verb) pair is only flagged
# if (a) the subject is an animal whose biological class (per WordNet) is
# in IMPOSSIBLE_BY_CLASS and (b) the verb is one of the impossibilities of that
# class, and (c) the text AFFIRMS it. When it fails, it fails toward silence
# (lets an absurd sentence through and the character responds normally), which is
# much cheaper than interrupting a legitimate sentence.
#
# DELIBERATELY NOT FLAGGED (design decision, change it here if you want):
#   - People flying/doing magic: in fantasy that's normal ("the wizard flies").
#   - Objects with living-being verbs: "the sword sings", "the door groans",
#     "the wind whispers" are figurative language, very common in roleplay.
#   - Negated sentences, questions and conditionals ("dogs don't fly", "can a
#     dog fly?", "if the dog flew"): they assert nothing, and a negation is
#     exactly the CORRECT statement.
#
# ASSUMED COST: recall drops (few absurd sentences are detected: today
# only animals + physically impossible verbs). See tests/
# test_contradiction.py for the measured figures.

# biological class -> verbs (lemma) that this class CANNOT do.
# Keep it SHORT and only with impossibilities that have no figurative ambiguity
# ("the salmon run" exists, which is why "run" is NOT in fish).
IMPOSSIBLE_BY_CLASS = {
    "fish":      {"fly", "walk"},
    "mammal":    {"fly"},
    "reptile":   {"fly"},
    "amphibian": {"fly"},
}

# Words that WordNet classifies into a class above but that DO fly
# (bat) or are flying fantasy creatures. Extend as needed.
FLYING_EXEMPT = {
    "bat", "dragon", "wyvern", "griffin", "gryphon", "hippogriff", "pegasus",
    "phoenix", "harpy", "gargoyle", "drake", "wyrm", "fairy", "sprite",
    "imp", "chimera", "roc", "thunderbird",
}

# Classes checked first: if something is a bird/insect/bat, it NEVER
# falls into "mammal"/"reptile" by accident (bat.n.01 descends from mammal).
_CLASS_ANCHORS = [
    ("bird",      "bird.n.01"),
    ("insect",    "insect.n.01"),
    ("bat",       "bat.n.01"),
    ("fish",      "fish.n.01"),
    ("mammal",    "mammal.n.01"),
    ("reptile",   "reptile.n.01"),
    ("amphibian", "amphibian.n.03"),
]

_CONDITIONAL_MARKS = {"if", "unless", "whether", "though", "although"}

_class_cache = {}


def animal_class(word):
    """Biological class of `word` according to WordNet (noun.animal senses only),
    or None if it is not a recognizable animal. Cached."""
    if word in _class_cache:
        return _class_cache[word]
    result = None
    try:
        from nltk.corpus import wordnet as wn
        anchors = [(k, wn.synset(v)) for k, v in _CLASS_ANCHORS]
        for s in wn.synsets(word, pos=wn.NOUN):
            if s.lexname() != "noun.animal":
                continue
            ancestors = {h for path in s.hypernym_paths() for h in path}
            for name, anchor in anchors:
                if anchor in ancestors:
                    result = name
                    break
            if result:
                break
    except Exception:
        result = None
    _class_cache[word] = result
    return result


def is_clearly_impossible(subj, act, concepts_db):
    """True only if (subj, act) is an impossibility from IMPOSSIBLE_BY_CLASS.
    The explicit wins: if `act` is in the subject's `related` (bird->fly)
    it is never a contradiction."""
    node = concepts_db.get(subj, {})
    if act in node.get("related", {}):
        return False
    if node.get("type") != "subject" or node.get("subtype") != "animal":
        return False
    if act == "fly" and subj in FLYING_EXEMPT:
        return False
    cls = animal_class(subj)
    return cls is not None and act in IMPOSSIBLE_BY_CLASS.get(cls, ())


def is_non_assertive(verb_tok):
    """True if the clause of `verb_tok` does not ASSERT the fact: negated,
    question or conditional. Takes a spaCy token."""
    for child in verb_tok.children:
        if child.dep_ == "neg":
            return True
        if child.dep_ == "mark" and child.lower_ in _CONDITIONAL_MARKS:
            return True
        # negated auxiliary: "does not fly", "can't fly"
        if child.dep_ in ("aux", "auxpass") and any(g.dep_ == "neg" for g in child.children):
            return True
    if verb_tok.sent.text.strip().endswith("?"):
        return True
    return False
