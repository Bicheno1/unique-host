# db/db_emotion.py — UNIQUE HOST
#
# Same problem db_danger.py solved for danger words, but for ordinary
# emotion vocabulary: CONCEPTS is a small hand-authored graph, so a plain
# word like "joy", "anger", "sadness", "gratitude" or "fear" had NO entry
# of its own and fell through resolve_concept()'s LEXICON fallback with an
# EMPTY related -- Delia had no reaction whatsoever to being told "I'm so
# happy" or "I'm furious", positive or negative, regardless of context.
#
# An audit of LEXICON's "emotion" category (64 words) found 57 with no
# push at all -- effectively the entire everyday emotional vocabulary
# (anger, joy, sadness, fear, hope, gratitude, surprise, shame...) was
# unreachable, while only violence/threat-adjacent words (grief, horror,
# panic, terror, torture, love) had real values, because those came from
# db_danger.py or a hand-authored sense.
#
# EVERY template below reuses TAGS THAT ALREADY EXIST in db_somatic.py /
# db_mental.py -- this file adds no new calibration numbers, it only makes
# already-calibrated emotional dimensions (joy, sadness, affection, trust,
# curiosity, identity, anticipation, cognitive_threat, seek_exit...)
# reachable from the plain words a person actually uses to name them.
#
# Same mechanism as db_danger.py (mirrored on purpose, not reinvented):
# apply_emotion(CONCEPTS) is called once at import time from
# db/db_concepts.py, right after apply_danger(). A hand-authored word is
# never overwritten; only its still-empty inflected forms get the push.

# type/subtype for a word in neither CONCEPTS nor the lexicon
FALLBACK_TYPE = {
    "anger":   ("status", "emotion"), "fear":  ("status", "emotion"),
    "joy":     ("status", "emotion"), "warmth": ("status", "emotion"),
    "sadness": ("status", "emotion"), "shame": ("status", "emotion"),
    "pride":   ("status", "emotion"), "awe":   ("status", "emotion"),
    "meta":    ("status", "emotion"),
}

# Each template is wrapped under a single "self" sense (like the "love" and
# "loved_person" concepts elsewhere) -- these words describe the speaker's
# OWN feeling, not a multi-sense external object like "monster" (fear /
# threat / danger senses). concepts_db's related-dict shape always expects
# {sense_name: {"somatic": [...], "mental": [...]}}, hence the wrapper.
EMOTION_TEMPLATES = {
    # confrontational arousal -- physiologically close to fear (real
    # activation), reuses the same recalibrated I-leaning tags
    "anger":  {"self": {"somatic": ["adrenaline", "muscle_tension"], "mental": ["cognitive_threat"]}},
    # being afraid / being on the receiving end of hostility
    "fear":   {"self": {"somatic": ["adrenaline", "cortisol"],        "mental": ["seek_exit", "cognitive_threat"]}},
    # reward / positive activation
    "joy":    {"self": {"somatic": ["dopamine", "endorphins"],        "mental": ["joy"]}},
    # bonded, relational warmth -- same tags used for "love" and "loved_person"
    "warmth": {"self": {"somatic": ["oxytocin", "safe_presence"],     "mental": ["affection", "trust", "relief"]}},
    # low-energy, deflated
    "sadness": {"self": {"somatic": ["fatigue"],                       "mental": ["sadness"]}},
    "shame":  {"self": {"somatic": [],                                 "mental": ["guilt"]}},
    # self-concept, forward-looking drive
    "pride":  {"self": {"somatic": ["dopamine"],                       "mental": ["identity", "anticipation"]}},
    "awe":    {"self": {"somatic": ["curiosity_pull"],                 "mental": ["curiosity"]}},
    # abstract/meta words ("emotion", "mood") that name having a feeling
    # without naming which one -- deliberately minimal, not zero
    "meta":   {"self": {"somatic": [],                                 "mental": ["clarity"]}},
}

EMOTION_WORDS = {
    "anger":  ["anger", "fury", "rage", "outrage", "temper", "frustration", "hatred", "spite", "envy"],
    "fear":   ["fear", "fears", "alarm", "shock", "surprise", "surprises", "harassment"],
    "joy":    ["joy", "delight", "pleasure", "enjoyment", "excitement", "enthusiasm", "satisfaction",
               "humour", "favour", "liking", "passion", "appetite", "desire", "desires",
               "preference", "preferences"],
    "warmth": ["affection", "attachment", "gratitude", "forgiveness", "compassion", "pity", "relief"],
    "sadness": ["sadness", "disappointment", "distress", "resignation", "surrender"],
    "shame":  ["shame"],
    "pride":  ["pride", "ego", "ambition", "hope", "hopes"],
    "awe":    ["awe", "wonders"],
    "meta":   ["emotion", "emotions", "feelings", "sentiment", "mood"],
}


def _copy(related):
    return {g: {"somatic": list(b["somatic"]), "mental": list(b["mental"])} for g, b in related.items()}


def apply_emotion(concepts):
    """Adds the intrinsic emotion tags to `concepts` (the CONCEPTS dict). Idempotent.
    Mirrors db_danger.py::apply_danger exactly -- same inflection handling,
    same "never overwrite a hand-authored push" rule -- just a different
    word list and templates. Reuses db_danger's own inflection helpers
    rather than duplicating them.
    """
    from db.db_lexicon import LEXICON
    from db.db_danger import _spread_inflections
    for template, words in EMOTION_WORDS.items():
        for word in words:
            node = concepts.get(word)
            if node is not None and node.get("related"):
                # hand-authored (or already given a push by db_danger.py,
                # e.g. "love") -- never overwritten, but its inflected
                # forms still need the push spread to them
                if not node.get("inflection_of"):
                    _spread_inflections(concepts, word, node)
                continue
            # type is ALWAYS "status", never taken from LEXICON's WordNet-
            # derived node_type (unlike db_danger.py, which lets an entity
            # word like "bandit" stay type "subject"). Every word here
            # names the SPEAKER'S OWN internal feeling, never an external
            # being -- letting WordNet's node_type leak through occasionally
            # mislabels one "subject" (LEXICON's generic person/animal
            # supersense), which makes it eligible for the Calibration
            # System's entity-tracking and _get_focus()'s subject-priority
            # rule. A feeling is not an entity that can be attacked, and
            # must never become the scene's focus over an actual character.
            if node is None:
                entry = LEXICON.get(word)
                synonyms = list(entry.get("synonyms", [])) if entry else [word]
                node = {"sense": None, "type": "status", "subtype": "emotion",
                         "synonyms": synonyms, "related": {}}
                concepts[word] = node
            else:
                node["type"], node["subtype"] = "status", "emotion"
            node["related"] = _copy(EMOTION_TEMPLATES[template])
            node["intrinsic_emotion"] = template
            _spread_inflections(concepts, word, node, template=None)
