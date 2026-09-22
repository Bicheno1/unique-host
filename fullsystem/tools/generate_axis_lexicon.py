"""
generate_axis_lexicon.py
-------------------------------------------------------------------------
Generates the per-axis lexicon (North/South/East/West) from the 10,000
most common English words (wordfreq).

- Excludes "subject" nouns (dog, cat, person, uncle, etc.) — only verbs
  and adjectives remain.
- Pronouns (I, you, we, us, etc.) do NOT come from this automatic list:
  they are already closed by hand in AXIS_NORTH/AXIS_SOUTH/AXIS_EAST/AXIS_WEST.
- Verbs: their 3 forms are generated (base/present, past, future with "will")
  using real conjugation (lemminflect, handles irregulars: have/has/had,
  go/went, be/was/were, etc.)
    -> past            => SOUTH axis
    -> future ("will")  => NORTH axis
    -> base/present     => no fixed axis (neutral, neither past nor future)
- Adjectives: heuristic based on WordNet definitions (glosses).
  Counts sensory-domain keywords (East) vs. evaluative/relational
  (West) in the definitions. If there is no clear signal, it is marked UNCLASSIFIED
  for manual review — a classification is NOT forced at random.

Output: db_axis_lexicon_generated.py
-------------------------------------------------------------------------
"""

from collections import Counter, defaultdict
from wordfreq import top_n_list
from nltk.corpus import wordnet as wn
from nltk.corpus import brown
from lemminflect import getInflection

N_WORDS = 10000

EAST_KEYWORDS = {
    "color", "colour", "temperature", "hot", "cold", "warm", "cool",
    "sound", "loud", "quiet", "noise", "pitch", "taste", "flavor",
    "flavour", "smell", "odor", "odour", "scent", "touch", "texture",
    "rough", "smooth", "size", "shape", "weight", "heavy", "light",
    "wet", "dry", "speed", "fast", "slow", "bright", "dark", "physical",
    "sensation", "visual", "tactile", "auditory", "olfactory",
    "gustatory", "surface", "density", "volume", "pressure",
}

WEST_KEYWORDS = {
    "moral", "ethical", "aesthetic", "beauty", "beautiful", "value",
    "virtue", "virtuous", "quality", "judgment", "judgement",
    "standard", "character", "behavior", "behaviour", "social",
    "ideal", "worthy", "desirable", "admirable", "pleasing",
    "attractive", "proper", "appropriate", "deserving", "fitting",
    "praiseworthy", "respectable", "honorable", "honourable",
    "fair", "just", "right", "wrong", "good", "bad", "excellent",
    "correct", "acceptable", "reputation", "esteem",
}


def dominant_pos(word, brown_counts):
    """Real dominant grammatical POS, measured on the Brown corpus."""
    counts = brown_counts.get(word)
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def classify_adjective(word):
    """East/West heuristic based on WordNet definitions."""
    synsets = [s for s in wn.synsets(word) if s.pos() in ("a", "s")]
    if not synsets:
        return "UNCLASSIFIED"
    east_score = 0
    west_score = 0
    for syn in synsets[:3]:  # only the most common senses
        gloss = syn.definition().lower()
        east_score += sum(1 for kw in EAST_KEYWORDS if kw in gloss)
        west_score += sum(1 for kw in WEST_KEYWORDS if kw in gloss)
    if east_score == 0 and west_score == 0:
        return "UNCLASSIFIED"
    return "EAST" if east_score > west_score else "WEST"


def main():
    print("Cargando corpus Brown (POS real)...")
    tagged = brown.tagged_words(tagset="universal")
    brown_counts = defaultdict(Counter)
    for word, tag in tagged:
        brown_counts[word.lower()][tag] += 1

    print(f"Loading top {N_WORDS} English words...")
    words = top_n_list("en", N_WORDS)

    verbs_base = []
    adjectives_east = []
    adjectives_west = []
    adjectives_unclassified = []

    skip_pronouns = {
        "i", "me", "my", "mine", "myself",
        "you", "your", "yours", "yourself",
        "we", "us", "our", "ours", "ourselves",
        "he", "him", "his", "himself", "she", "her", "hers", "herself",
        "they", "them", "their", "theirs", "themselves",
        "it", "its", "itself", "that", "this", "those", "these",
    }

    # modals: Brown tags them as VERB, but they are not conjugable verbs
    # (lemminflect breaks them: "shoulded", "will could", "doesn't should").
    # They already live by hand, with their real forms, in db_axis_lexicon.py.
    skip_modals = {
        "will", "would", "can", "could", "may", "might", "shall",
        "should", "must", "ought",
    }

    for w in words:
        if not w.isalpha():
            continue
        if w in skip_pronouns:
            continue  # already closed by hand in the 4 axes
        if w in skip_modals:
            continue  # already closed by hand, they are not conjugable verbs

        pos = dominant_pos(w, brown_counts)
        if pos == "VERB":
            verbs_base.append(w)
        elif pos == "ADJ":
            axis = classify_adjective(w)
            if axis == "EAST":
                adjectives_east.append(w)
            elif axis == "WEST":
                adjectives_west.append(w)
            else:
                adjectives_unclassified.append(w)
        # NOUN, ADV, DET, ADP, CONJ, PRON, NUM, PRT, X -> excluded (subjects, function words)

    print(f"Verbs found: {len(verbs_base)}")
    print(f"East adjectives: {len(adjectives_east)}")
    print(f"West adjectives: {len(adjectives_west)}")
    print(f"Unclassified adjectives (manual review): {len(adjectives_unclassified)}")

    # -- generate verb forms --------------------------------------------
    IRREGULAR_3SG = {"have": "has", "be": "is", "do": "does", "go": "goes"}

    verb_forms = {}
    for v in verbs_base:
        try:
            past = getInflection(v, tag="VBD")
            past = past[0] if past else None
        except Exception:
            past = None

        third_sg = IRREGULAR_3SG.get(v)
        if third_sg is None:
            try:
                third_sg = getInflection(v, tag="VBZ")
                third_sg = third_sg[0] if third_sg else v
            except Exception:
                third_sg = v

        if v == "be":
            # "be" is an irregular auxiliary: it doesn't use doesn't/don't/didn't
            neg = {
                "negative_present": "isn't",
                "negative_present_you_we": "aren't",
                "negative_past": "wasn't / weren't",
                "negative_future": "won't be",
            }
        else:
            neg = {
                "negative_present": f"doesn't {v}",
                "negative_present_you_we": f"don't {v}",
                "negative_past": f"didn't {v}",
                "negative_future": f"won't {v}",
            }

        verb_forms[v] = {
            "present": v,
            "past": past,               # -> SOUTH axis
            "future": f"will {v}",      # -> NORTH axis
            **neg,                       # -> SOUTH axis (negation/impossibility)
        }

    # -- write output file ------------------------------------------
    with open("db_axis_lexicon_generated.py", "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("db_axis_lexicon_generated.py\n")
        f.write("Automatically generated by generate_axis_lexicon.py\n")
        f.write(f"Source: top {N_WORDS} English words (wordfreq) + real POS (Brown corpus)\n")
        f.write("Pronouns/subjects are NOT here: they live by hand in db_axis_lexicon.py\n")
        f.write("East/West adjectives are a heuristic (WordNet glosses) -- review\n")
        f.write('"""\n\n')

        f.write("# Verbs: base, past (-> SOUTH), future with 'will' (-> NORTH)\n")
        f.write("VERB_TENSES = {\n")
        for v, forms in verb_forms.items():
            f.write(f"    {v!r}: {forms!r},\n")
        f.write("}\n\n")

        f.write("# Adjectives -- raw perception of one sense (WordNet heuristic)\n")
        f.write(f"ADJECTIVES_EAST = {sorted(adjectives_east)!r}\n\n")

        f.write("# Adjectives -- relation between parts / judgment against a standard (WordNet heuristic)\n")
        f.write(f"ADJECTIVES_WEST = {sorted(adjectives_west)!r}\n\n")

        f.write("# Adjectives with no clear signal in the definition -- need manual review\n")
        f.write(f"ADJECTIVES_UNCLASSIFIED = {sorted(adjectives_unclassified)!r}\n")

    print("\nFile generated: db_axis_lexicon_generated.py")


if __name__ == "__main__":
    main()
