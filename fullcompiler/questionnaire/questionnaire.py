# character/questionnaire.py — UNIQUE HOST
#
# CHARACTER CREATOR — fixed questionnaire → character.json
#
# TAXONOMY (confirmed) — four explicit groups,
# in the order they're asked:
#
#   PRIMARY — FORTITUDE (8)     -> base_state: resting point of both engines
#   PRIMARY — CHEMISTRY (20)    -> Category Bias (4, which of the 4 rows
#                                   Danger/Benefit/Neutral/Unclassifiable
#                                   wins first) + Axis Gain (16, which of
#                                   a row's 4 responses wins once it's
#                                   active). Both are "primary" because,
#                                   like Fortitude, they apply generally —
#                                   they tune the SAME chemical/response
#                                   system regardless of which concept
#                                   triggered it, no per-word question.
#   SECONDARY — IDENTITY (4)    -> name/age/height/physical_traits: who
#                                   the character IS, not a concept push.
#   TERTIARY — CONCEPTS (4)     -> family_opinion, animals_opinion,
#                                   core_fear, core_comfort: hand-tunes
#                                   or overrides how specific concepts
#                                   push the engines.
#
# PRIMARY (Fortitude + Chemistry, 28 questions total) is what makes the
# WHOLE lexicon work without a per-word question: any of the ~5,000 words
# in db/db_lexicon.py resolves to a raw {V,I,Lv,Gv} push from its own
# meaning (already fixed, independent of the character), and PRIMARY
# decides how THIS character reads and reacts to that push. TERTIARY is
# the only group that talks about specific words/concepts, and it only
# exists to hand-tune or override a handful of cases — everything else
# is already covered by PRIMARY. SECONDARY (identity) doesn't push the
# engines at all — it's descriptive, used by core/construction_matcher.py
# to keep the character's own name out of subject extraction.
#
# See chemical_system_docs/ for the full design rationale:
#   - chemical_system_axis_gain_questions_english.md  (chemistry/gain wording)
#   - chemical_system_questionnaire_design.md          (chemistry/bias rationale)

# ── PRIMARY — FORTITUDE (8 questions, 1 per axis) ────────────────────────
# Each cognitive profile (Abstract/Logical/Structural/Sensory) maps to
# ONE somatic axis + ONE mental axis. Answers are 1-10 and convert
# DIRECTLY (linear) to each axis's base value, scaled to the
# "normal use" functional range (0-50, db/db_somatic.py + db_mental.py).
QUESTIONS_PRIMARY_FORTITUDE = [
    # (key, label, type, extra)
    ("fort_V",  "How positive are they?",                              "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_P",  "How much of a dreamer are they?",                     "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_I",  "How much do they worry that something will go wrong?","slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_A",  "How much do they need things to make sense?",         "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_Gv", "How good are they at connecting ideas?",              "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_Rr", "How much do they enjoy solving hard problems?",       "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_Lv", "How impulsive are they?",                             "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fort_Er", "How emotional are they?",                             "slider", {"minimum": 1, "maximum": 10, "value": 5}),
]

# ── PRIMARY — CHEMISTRY (20 questions: 4 Category Bias + 16 Axis Gain) ──
# Category Bias: how easily this character classifies ANY input as
# Danger / Benefit / Neutral / Unclassifiable in the first place — widens
# or narrows that row's threshold, before Axis Gain even gets asked which
# response wins.
# Axis Gain: once a row is active, which of its 4 responses wins
# (Attack vs Surrender vs ...). Verbatim from
# chemical_system_docs/chemical_system_axis_gain_questions_english.md.
QUESTIONS_PRIMARY_CHEMISTRY = [
    # -- Category Bias --
    ("bias_danger",         "How easily does something feel like a real threat to them, rather than a minor annoyance?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("bias_benefit",        "How easily do they enjoy simple, everyday things, without needing something big to feel good?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("bias_neutral",        "How comfortable are they when everything is predictable and orderly, with nothing special happening?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("bias_unclassifiable", "How comfortable are they not knowing what something is, before needing to resolve or label it?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Axis Gain: Danger --
    ("gain_danger_V",  "How likely is this character to confront a threat head-on instead of avoiding it?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_danger_I",  "How quickly does their body freeze or shut down when there's no way to fight or flee?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_danger_Gv", "How oriented are they toward organizing a defense or protecting others instead of just reacting on their own?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_danger_Lv", "How quickly do they prioritize escaping or putting distance between themselves and danger, before weighing whether to fight?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Axis Gain: Benefit --
    ("gain_benefit_V",  "How intensely does this character enjoy and let themselves be carried by something good happening to them?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_benefit_I",  "How much self-control does this character have against something tempting that they know isn't good for them?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_benefit_Gv", "How easily do they become emotionally activated by the wellbeing of someone specific close to them?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_benefit_Lv", "How indifferent are they to something good that doesn't directly affect them?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Axis Gain: Neutral / Classifiable --
    ("gain_neutral_V",  "How attentive are they to new things in their surroundings, even without urgency?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_neutral_I",  "How well do they filter out irrelevant background noise without getting distracted?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_neutral_Gv", "How much do they need to feel part of a group or in company, even when nothing special is happening?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_neutral_Lv", "How easily do they sustain focus on something without external pressure pushing them to?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Axis Gain: Unclassifiable --
    ("gain_unclassifiable_V",  "How curious are they about something completely unknown, with no obvious danger?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_unclassifiable_I",  "How easily do they let go of something once there's no longer a point in continuing?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_unclassifiable_Gv", "How good a communicator are they when they need to convey something important without emergency urgency?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("gain_unclassifiable_Lv", "How much can they contain a strong, ambiguous emotion without it showing on the outside? (note: unlike the other 15 questions, a high score here is not the \"healthiest\" outcome — see systems/chemical_system.py MATRIX_MODES[('unclassifiable','Lv')] rebound)",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
]

# ── MENTAL CHEMISTRY ────────────────────────────────────────
# Mental twin of QUESTIONS_PRIMARY_CHEMISTRY above -- same 16
# modes, same 4 category rows, but measuring the mental/cognitive
# LEAN instead of the body's reaction. See
# systems/mental_state_system.py:release_from_axis_push.
QUESTIONS_PRIMARY_MENTAL_CHEMISTRY = [
    # -- Mental Category Bias --
    ("mental_bias_danger",         "How easily do their thoughts spiral toward worst-case scenarios, even before anything physical happens?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_bias_benefit",        "How easily do they mentally relax and let their guard down when things are actually going fine?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_bias_neutral",        "How comfortable are they mentally when there's nothing urgent to think about or plan for?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_bias_unclassifiable", "How comfortable are they leaving a thought or question mentally unresolved, without needing to figure it out right away?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Mental Axis Gain: Danger --
    ("mental_gain_danger_P",  "How likely are they to mentally confront a threat -- turning it over, facing it head-on in their thoughts -- instead of pushing it out of mind?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_danger_A",  "How quickly does their mind go blank or give up internally when a threat feels inescapable?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_danger_Rr", "How oriented is their thinking toward planning how to protect others, rather than just reacting internally on their own?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_danger_Er", "How quickly does their mind jump to escaping the thought itself -- distraction, denial -- before working through it?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Mental Axis Gain: Benefit --
    ("mental_gain_benefit_P",  "How fully do they let themselves mentally enjoy something good, without holding back or second-guessing it?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_benefit_A",  "How much do they mentally talk themselves out of something tempting, even once it already feels appealing?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_benefit_Rr", "How readily do their thoughts turn warm and trusting toward someone close when things are going well?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_benefit_Er", "How indifferent is their mind to something good that doesn't directly involve them?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Mental Axis Gain: Neutral / Classifiable --
    ("mental_gain_neutral_P",  "How mentally curious and attentive are they to new things around them, even without urgency?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_neutral_A",  "How easily does their mind filter out irrelevant background thoughts without getting distracted?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_neutral_Rr", "How much do they mentally think of themselves as part of a group, even when nothing in particular is happening?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_neutral_Er", "How much does their mind stay quietly planning or turning things over, even with nothing urgent going on?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),

    # -- Mental Axis Gain: Unclassifiable --
    ("mental_gain_unclassifiable_P",  "How drawn are they, mentally, to dig into something they don't understand rather than let it go?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_unclassifiable_A",  "How quickly do they mentally lose interest in or give up on something confusing?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_unclassifiable_Rr", "How readily do their thoughts turn to warning or alerting someone else about something unclear?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("mental_gain_unclassifiable_Er", "How much do they mentally clench up or hold tension in their thinking around something unresolved?",
        "slider", {"minimum": 1, "maximum": 10, "value": 5}),
]

# ── SECONDARY — IDENTITY (4 questions) ───────────────────────────────────
# Who the character IS. Descriptive only — doesn't push either engine;
# core/construction_matcher.py uses "name" to keep the character's own
# name out of subject extraction (see character/injector.py).
QUESTIONS_SECONDARY_IDENTITY = [
    ("name",        "Character name",                    "text",  {}),
    ("age",         "Age",                                "number", {"minimum": 1, "maximum": 120, "value": 25}),
    ("height_cm",   "Height (cm)",                        "number", {"minimum": 50, "maximum": 230, "value": 165}),
    ("physical_traits", "Physical traits (free text)",    "text",  {}),
    # Optional identity data. These used to be added by hand to
    # the JSON (e.g. delia_adventurer_v2.json); now the compiler generates
    # them. They are host identity data ONLY: they are NOT seeded as
    # concepts (names are created by memory at runtime).
    ("father_name", "Father's name (optional)",            "text",  {}),
    ("mother_name", "Mother's name (optional)",            "text",  {}),
    ("pet_name",    "Pet's name (optional)",               "text",  {}),
    ("friend_name", "Closest friend's name (optional)",    "text",  {}),
]

# ── TERTIARY — CONCEPTS (8 questions) ────────────────────────────────────
# Hand-authored overrides for specific concepts (family, animals, a
# named fear/comfort) — the only questions that talk about a particular
# word/concept rather than tuning the engines in general.
#
# MIGRATION 2026-09-0X (the design notes): the 4 GROUP questions below
# (people/environment/world_objects/supernatural) replace the fixed,
# universal "related" tag lists that db/db_concepts.py hand-authored for
# ~25 of its ~58 concepts (person/animal/environment/object/illogical
# groups — see WORLD_GROUPS below). Each group answer cascades the SAME
# 1-10 value to every word in WORLD_GROUPS[key]["words"] via
# _add_valenced_concept, same mechanism as family_opinion/
# animals_opinion — no per-word sub-question, to
# keep the questionnaire short. animals_opinion is REUSED (not
# duplicated) for fish/bird/duck, which weren't personalized before.
#
# NOT migrated (confirmed 2026-09-0X, checked first): the ~10 "status"
# concepts (danger/threat/alone/safe/calm/scared/tired/quiet/aggressive/
# tone) stay on their fixed universal tags. Checked whether they're
# already covered elsewhere before touching anything (as instructed):
# core/lexicon_bridge.py's ~120-word valence list does NOT contain any
# of them (only "quiet" appears, and only as a scope/Lv word with no
# valence sign), and db/db_lexicon.py only carries WordNet category, not
# a push vector. So they are NOT yet redundant — retiring them now would
# be a real regression (e.g. the demo's "safe light" input would lose
# "safe" entirely), not a cleanup. They aren't "opinions of a thing"
# anyway (nobody rates "danger" 1=dislike..10=love the way they rate
# coffee) — their personalization already happens through a different,
# already-implemented path (Category Bias + Axis Gain in
# systems/chemical_system.py, see its LEGACY_TRIGGER_TO_MODES shim).
# Revisit only once a real per-word sentiment source lands (state doc
#  item 6) and can replace their fixed tags with something equally
# real. Verbs (run/walk/hide/breathe/fly) and grammar glue
# (self/tu/es/name/identity/question words/tone_es) were left alone for
# the same reason — not "opinion of a thing" concepts.
QUESTIONS_TERTIARY_CONCEPTS = [
    ("family_opinion", "What do they think of their family? (1=hostile, 10=loving)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("animals_opinion", "How do they feel about animals? (1=fear/dislike, 10=love)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("people_opinion", "How do they feel about people in general? (1=distrust, 10=warmth)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("environment_opinion", "How do they feel about the places/environments around them? (1=unsettling, 10=comforting)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("world_objects_opinion", "How do they feel about everyday objects/things around them? (1=indifferent/wary, 10=find comfort in them)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("supernatural_opinion", "How do they feel about the supernatural/unexplainable? (1=terrifying, 10=fascinating)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fantasy_opinion", "How do they feel about magic and fantastical creatures — wizards, dragons, monsters? (1=terrifying, 10=fascinating)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("fantasy_objects_opinion", "How do they feel about magical objects and places — potions, relics, cursed ruins? (1=unsettling, 10=alluring)", "slider", {"minimum": 1, "maximum": 10, "value": 5}),
    ("core_fear",   "Something they are deeply afraid of (free text, optional)", "text", {}),
    ("core_comfort","Something that calms/reassures them (free text, optional)", "text", {}),
    # ── IDENTITY ANCHORS ────────────────────────────────
    # What sustains purpose/security/company/structure for as long as
    # nothing contradicts it -- see core_identity.py:IdentityAnchorSystem.
    # Same pattern as core_fear/core_comfort: a free word that becomes a
    # recognizable concept; whenever it shows up WITHOUT a loss/negation
    # word next to it (THREAT_MARKERS), it slowly feeds its stat. If they
    # show up together (e.g. "family" + "dead"), it flips it -- a strong
    # push downward.
    ("purpose_source",  "What gives them a sense of purpose or meaning? (free text, e.g. 'being kind', 'being the strongest', 'protecting people')", "text", {}),
    ("security_source", "What makes them feel secure/safe? (free text, e.g. 'being armed', 'being around people', 'familiar ground')", "text", {}),
    ("valued_bond",      "Who or what do they value most? (free text, e.g. 'my family', 'my dog', 'my best friend')", "text", {}),
    ("structure_source", "What gives their life a sense of order? (free text, e.g. 'a fixed routine', 'a place to return to', 'a plan')", "text", {}),
]

# ── WORLD GROUPS — words each group question cascades to ────────────────
# (name, sense, subtype, synonyms) tuples, lifted from the old hand-
# authored db/db_concepts.py entries (same sense/subtype/synonyms kept,
# only the "related" push changes — from fixed universal tags to a
# per-character dynamic valence__<name> tag). biological follows the
# node_type each word landed on after the lexicon fix.
WORLD_GROUPS = {
    "people_opinion": {
        "biological": True,
        "concept_type": "subject",
        "words": [
            ("person",  "sight", "social",       ["someone", "people", "human"]),
            ("face",    "sight", "social",       ["expression"]),
        ],
    },
    "animals_opinion": {
        # "animal" itself is already hand-picked above (biological=True) —
        # this group only ADDS the 3 species words that weren't
        # personalized before, reusing the same answer, no new question.
        "biological": True,
        "concept_type": "subject",
        "words": [
            ("fish", "sight", "animal", ["salmon"]),
            ("bird", "sight", "animal", ["bird", "small-bird", "eagle", "dove"]),
            ("duck", "sight", "animal", ["anatidae"]),
        ],
    },
    "environment_opinion": {
        "biological": False,
        "concept_type": "environment",
        "words": [
            ("room",   "sight", "built",   ["chamber"]),
            ("dark",   "sight", "condition", ["darkness", "dim"]),
            ("light",  "sight", "condition", ["bright", "lamp"]),
            ("night",  "sight", "time",    ["midnight", "evening"]),
            ("forest", "sight", "natural", ["woods", "jungle"]),
            ("house",   "sight", "built",   ["home", "house"]),
            ("place",  "sight", "natural", ["spot", "site"]),
            ("street", "sight", "outdoor", ["outside", "outdoor", "open"]),
        ],
    },
    "world_objects_opinion": {
        "biological": False,
        "concept_type": "object",
        "words": [
            ("food",   "sight", "consumable", ["meal", "eat"]),
            ("water",  "sight", "consumable", ["drink", "liquid"]),
            ("money",  "sight", "resource",   ["cash", "resource"]),
            ("key", "sight", "tool",       ["keys", "key"]),
            ("door",   "sight", "structure",  ["gate", "entrance"]),
            ("window", "sight", "structure",  ["glass", "pane"]),
            ("melody", "hearing", "melodic_phrase",
                ["melody", "tune", "song", "music", "beautiful_song"]),
        ],
    },
    "supernatural_opinion": {
        "biological": False,
        "concept_type": "illogical",
        "words": [
            ("ghost",  "sight", "apparition", ["spirit", "phantom", "specter", "apparition"]),
            ("shadow", "sight", "apparition", ["shade", "silhouette"]),
            ("corpse", "sight", "presence",   ["body"]),
        ],
    },
    # ── FANTASY — high-fantasy creatures/objects. Same "not
    # in the top-N general-English lexicon" gap fixed for db_lexicon.py
    # via tools/generate_lexicon.py:FANTASY_WORDS — this group is what
    # actually gives each of those words a per-character push, same
    # pattern as supernatural_opinion above for ghost/shadow/corpse.
    # Split into creatures (biological=True, pulls Gv/empathy like a
    # person or animal would) and objects/places (biological=False,
    # pulls Lv/Er like an inanimate thing or event would).
    "fantasy_opinion": {
        "biological": True,
        "concept_type": "subject",
        "words": [
            ("wizard",      "sight", "spellcaster", ["mage", "sorcerer", "magician"]),
            ("witch",       "sight", "spellcaster", ["sorceress", "enchantress"]),
            ("elf",         "sight", "creature",     ["brownie", "gremlin"]),
            ("dwarf",       "sight", "creature",     ["gnome"]),
            ("orc",         "sight", "creature",     ["ork"]),
            ("goblin",      "sight", "creature",     ["hobgoblin", "hob"]),
            ("troll",       "sight", "creature",     []),
            ("ogre",        "sight", "creature",     ["fiend"]),
            ("demon",       "sight", "creature",     ["daemon", "devil"]),
            ("vampire",     "sight", "creature",     ["lamia"]),
            ("werewolf",    "sight", "creature",     ["lycanthrope"]),
            ("zombie",      "sight", "creature",     ["undead", "living dead"]),
            ("skeleton",    "sight", "creature",     ["bones"]),
            ("dragon",      "sight", "creature",     ["firedrake", "wyvern"]),
            ("griffin",     "sight", "creature",     ["gryphon"]),
            ("fairy",       "sight", "creature",     ["faerie", "sprite"]),
        ],
    },
    "fantasy_objects_opinion": {
        "biological": False,
        "concept_type": "object",
        "words": [
            ("potion",   "sight", "consumable", ["elixir", "brew"]),
            ("wand",     "sight", "tool",       ["staff_magic"]),
            ("amulet",   "sight", "object",     ["talisman"]),
            ("scroll",   "sight", "object",     ["tome"]),
            ("relic",    "sight", "object",     ["artifact"]),
            ("portal",   "sight", "structure",  ["gateway"]),
            ("throne",   "sight", "structure",  []),
            ("crypt",    "sight", "structure",  ["catacomb"]),
            ("curse",    "internal", "emotional", ["hex", "jinx"]),
            ("ritual",   "internal", "emotional", ["rite"]),
            ("prophecy", "internal", "emotional", ["prognostication"]),
        ],
    },
}

# Flat, ordered list — kept for existing callers (app.py builds its
# Gradio form by iterating QUESTIONS in order; build_character_json below
# reads answers by key regardless of grouping).
# ── World/likes tree questions (character/tree_questionnaire.py) ────────
from questionnaire.tree_questionnaire import TREE_QUESTIONS

QUESTIONS = (
    QUESTIONS_SECONDARY_IDENTITY
    + QUESTIONS_PRIMARY_FORTITUDE
    + QUESTIONS_PRIMARY_CHEMISTRY
    + QUESTIONS_PRIMARY_MENTAL_CHEMISTRY
    + QUESTIONS_TERTIARY_CONCEPTS
    + TREE_QUESTIONS
)

# "Normal use" functional range per db_somatic.py / db_mental.py comments
FORTITUDE_TARGET_RANGE = 50.0

# Row keys as used throughout core/response_matrix.py + systems/chemical_system.py
CATEGORIES = ["danger", "benefit", "neutral", "unclassifiable"]
AXES       = ["V", "I", "Gv", "Lv"]
MENTAL_AXES = ["P", "A", "Rr", "Er"]   # ver systems/mental_state_system.py::MENTAL_AXIS_MAP


def _fortitude_scale(value_1_10: float) -> float:
    """Direct linear conversion: 1-10 -> 0-50 (normal-use functional range)."""
    value_1_10 = max(1.0, min(10.0, float(value_1_10)))
    return (value_1_10 / 10.0) * FORTITUDE_TARGET_RANGE


def _scale(value_1_10: float, lo: float, hi: float) -> float:
    """Generic linear map from a 1-10 scale to [lo, hi] — used by the
    still-placeholder core_identity_rules section (family/animals)."""
    value_1_10 = max(1.0, min(10.0, float(value_1_10)))
    return lo + (value_1_10 - 1.0) / 9.0 * (hi - lo)


from questionnaire.valence import compute_concept_push
from questionnaire.tree_questionnaire import populate_tree_concepts, compile_related
from lexicon_db.db_lexicon import LEXICON


def _clean_answers(answers: dict) -> dict:
    """Normalizes the answers BEFORE compiling (2026-09-19).

    - slider/number: converted to float; None, "" or non-numeric text is
      discarded (the usual default value applies). Out-of-range values are
      clamped to the minimum/maximum the question itself declares.
    - text: trimmed with strip(); None or whitespace-only is discarded.
    - unknown keys pass through unchanged.
    Returns a copy; does not modify `answers`.
    """
    clean = dict(answers or {})
    for key, _label, qtype, extra in QUESTIONS:
        if key not in clean:
            continue
        v = clean[key]
        if qtype in ("slider", "number"):
            try:
                if v is None or (isinstance(v, str) and not v.strip()):
                    raise ValueError
                f = float(v)
                if f != f or f in (float("inf"), float("-inf")):   # NaN / inf
                    raise ValueError
            except (TypeError, ValueError):
                del clean[key]
                continue
            lo, hi = extra.get("minimum"), extra.get("maximum")
            if lo is not None: f = max(float(lo), f)
            if hi is not None: f = min(float(hi), f)
            clean[key] = int(f) if (qtype == "number" and f == int(f)) else f
        elif qtype == "text":
            if v is None or not str(v).strip():
                del clean[key]
            else:
                clean[key] = str(v).strip()
    return clean


def build_character_json(answers: dict) -> dict:
    """
    Fortitude (base_state) comes DIRECTLY from the 8 confirmed 1-10
    questions — one linear conversion per axis, no derived formulas.
    category_bias (4) and chemical_gains (16) pass through as raw 1-10
    values — both systems/chemical_system.py (DEFAULT_GAINS) and
    core/response_matrix.py (DEFAULT_CATEGORY_BIAS) already expect exactly
    this 1-10 scale (multiplier = 0.5 + value/10), so no rescaling needed
    here. Everything else below (core_identity_rules, concepts_seed,
    saturation_thresholds) is still placeholder pending the world/likes
    tree and the author's real saturation formulas.
    """
    answers = _clean_answers(answers)

    # ── Layer 1 — Fortitude — direct 1-10 -> 0-50 conversion, one per axis ──
    V_base  = _fortitude_scale(answers.get("fort_V", 5))
    P_base  = _fortitude_scale(answers.get("fort_P", 5))
    I_base  = _fortitude_scale(answers.get("fort_I", 5))
    A_base  = _fortitude_scale(answers.get("fort_A", 5))
    Gv_base = _fortitude_scale(answers.get("fort_Gv", 5))
    Rr_base = _fortitude_scale(answers.get("fort_Rr", 5))
    Lv_base = _fortitude_scale(answers.get("fort_Lv", 5))
    Er_base = _fortitude_scale(answers.get("fort_Er", 5))

    # ── Layer 2 — category bias — raw 1-10, one per row ──────────────
    category_bias = {
        "danger":         float(answers.get("bias_danger", 5)),
        "benefit":        float(answers.get("bias_benefit", 5)),
        "neutral":        float(answers.get("bias_neutral", 5)),
        "unclassifiable": float(answers.get("bias_unclassifiable", 5)),
    }

    # ── Layer 3 — axis gain — raw 1-10, 4 per row, nested by category ──
    chemical_gains = {
        category: {
            axis: float(answers.get(f"gain_{category}_{axis}", 5))
            for axis in AXES
        }
        for category in CATEGORIES
    }

    # ── Layer 2b/3b — mental twin — same pattern, for
    # mental_state_system.py:release_from_axis_push. The gains are
    # stored under the SOMATIC label (V/I/Gv/Lv) because MENTAL_AXIS_MAP
    # translates them at read time -- so there is no need to duplicate
    # DEFAULT_GAINS with another set of keys.
    mental_category_bias = {
        "danger":         float(answers.get("mental_bias_danger", 5)),
        "benefit":        float(answers.get("mental_bias_benefit", 5)),
        "neutral":        float(answers.get("mental_bias_neutral", 5)),
        "unclassifiable": float(answers.get("mental_bias_unclassifiable", 5)),
    }
    _MENTAL_TO_SOMATIC_AXIS = {"P": "V", "A": "I", "Rr": "Gv", "Er": "Lv"}
    mental_gains = {
        category: {
            _MENTAL_TO_SOMATIC_AXIS[m_axis]: float(answers.get(f"mental_gain_{category}_{m_axis}", 5))
            for m_axis in MENTAL_AXES
        }
        for category in CATEGORIES
    }

    family       = float(answers.get("family_opinion", 5))
    animals      = float(answers.get("animals_opinion", 5))

    # Saturation thresholds — TODO: placeholder, pending
    # real formula. For now derived loosely from Logical/I (worry) —
    # a character that worries more about things going wrong saturates sooner.
    worry = float(answers.get("fort_I", 5))
    mental_high  = 130.0 - worry * 7.0    # more worry -> lower threshold
    somatic_high = 260.0 - worry * 14.0

    # ── VALENCIA — general->specific concept push ──
    # Every 1-10 concept rating (family_opinion, animals_opinion, and the
    # two free-text slots below) maps to a full 4-axis push via
    # character/valence.py:compute_concept_push -- V/I/P/A come
    # straight from the value and its complement (universal); Lv/Gv and
    # Er/Rr are blended with THIS character's own Fortitude, so the same
    # rating leans toward empathy (Gv/Rr) or ego (Lv/Er) depending on who
    # is answering, not on the word itself. See character/valence.py for
    # the full rationale and the worked examples that confirmed this.
    fortitude_1_10 = {
        "fort_Gv": float(answers.get("fort_Gv", 5)),
        "fort_Lv": float(answers.get("fort_Lv", 5)),
        "fort_Rr": float(answers.get("fort_Rr", 5)),
        "fort_Er": float(answers.get("fort_Er", 5)),
    }

    # core_fear / core_comfort don't have their own 1-10 slider (free
    # text) -- pinned to the extremes of the scale they're meant to
    # represent: a "deeply afraid of" concept is as negative as the
    # scale goes (1), a "calms/reassures" concept is as positive as it
    # goes (10). If a future version adds an intensity slider for these,
    # swap these constants for the answer.
    CORE_FEAR_VALUE    = 1.0
    CORE_COMFORT_VALUE = 10.0

    tag_values_seed = {"somatic": {}, "mental": {}}
    concepts_seed = {}

    def _add_valenced_concept(name, value_1_10, sense, subtype, synonyms, biological,
                               related_key="valence", concept_type="subject"):
        """Registers one concept with its personalized push, wired through
        a dedicated dynamic tag (see character/injector.py, which merges
        tag_values_seed into db_somatic/db_mental's TAG_VALUES_* before
        concepts_seed is merged into db_concepts.CONCEPTS -- the tag must
        exist first). `biological` (confirmed 2026-09-05, §23) decides
        whether the value pulls Gv/Rr (biological/subject) or Lv/Er
        (non-biological/object) -- see character/valence.py.

        `related_key` -- core/pre_input.py::_get_multiplier() matches
        concepts by shared `related` KEYS, not values. A generic
        "valence" key for every hand-picked concept would make ANY two
        of them look "related" just by both being personalized (e.g.
        "ghost" + "money" would falsely multiply) -- the same pitfall
        the tree's compile_related() (character/tree_questionnaire.py,
        §23/28) exists to avoid for tree words. WORLD_GROUPS callers
        pass their own group_key here so only words in the SAME group
        share a key -- a real "shared branch" signal, not a coincidence
        of both having a personalized push. Left as the "valence"
        default for family/animal/core_fear/core_comfort, unchanged.

        `concept_type` -- FIX 2026-09-12: this used to be hardcoded to
        "subject" for every single concept regardless of caller, which
        silently overwrote the original hand-authored type of anything
        that already existed in db/db_concepts.py (e.g. "ghost" went
        from "illogical" to "subject" the moment a character answered
        supernatural_opinion, and "dark"/"forest" went from
        "environment" to "subject" via environment_opinion) --
        core/pre_input.py::get_focus()'s PRIORITY list
        (illogical > subject > action > status > environment > object)
        depends on this being correct to pick the right focus concept
        when a scene has several. Now passed through from each
        WORLD_GROUPS entry's own "concept_type" instead.
        """
        push = compute_concept_push(fortitude_1_10, value_1_10, biological)
        tag = f"valence__{name}"
        tag_values_seed["somatic"][tag] = push["somatic"]
        tag_values_seed["mental"][tag]  = push["mental"]

        # Fix:
        # this used to REPLACE the concept's "related" dict outright,
        # which silently deleted the legitimate capability links the
        # static db/db_concepts.py entry already had (e.g. "bird" ->
        # related={"fly":...}). core/pre_input.py:detect_contradiction
        # reads those exact keys as "things this subject can legitimately
        # do" -- once a character replaced "bird" via this function,
        # "fly" was gone and "a bird flies" started reading as a false
        # contradiction ("birds don't fly"). MERGE with whatever related
        # keys the static concept already has instead of overwriting, so
        # the valence group key sits ALONGSIDE the original capability
        # keys rather than erasing them.
        import lexicon_db.db_concepts as _db_concepts
        existing_related = dict(_db_concepts.CONCEPTS.get(name, {}).get("related", {}))
        existing_related[related_key] = {"somatic": [tag], "mental": [tag]}

        concepts_seed[name] = {
            "sense": sense, "type": concept_type, "subtype": subtype,
            "synonyms": synonyms,
            "related": existing_related,
        }

    _add_valenced_concept("family", family, "internal", "relation",
                           ["family", "parents", "home"],
                           biological=True)   # about people -- pulls Gv (empathy)
    _add_valenced_concept("animal", animals, "sight", "animal",
                           ["animal", "creature", "pet"],
                           biological=True)   # a living being -- pulls Gv

    # ── WORLD GROUPS (migration, see QUESTIONS_TERTIARY_CONCEPTS above) ──
    # Each group's answer cascades unchanged to every word in its list --
    # no per-word sub-question, same value for the whole group. Replaces
    # the fixed universal "related" tags those ~25 words had in
    # db/db_concepts.py with a per-character valence__<word> tag.
    for group_key, group in WORLD_GROUPS.items():
        group_value = float(answers.get(group_key, 5))
        for name, sense, subtype, synonyms in group["words"]:
            _add_valenced_concept(name, group_value, sense, subtype, synonyms,
                                   biological=group["biological"],
                                   related_key=f"group__{group_key}",
                                   concept_type=group.get("concept_type", "subject"))

    core_identity_rules = {
        "host_identity": {
            "type": "identity",
            "concepts": ["name", "identity", "self", "which", "who"],
            "effect": "none",
            "factor": 1.0,
            "value": {
                "name":   answers.get("name", "Unnamed"),
                "age":    answers.get("age", 25),
                "height": f"{answers.get('height_cm', 165)}cm",
                "traits": answers.get("physical_traits", ""),
            },
            "note": "Generated from questionnaire — host base identity.",
        },
        # family_bond / animal_affinity used to live here as an
        # amplify/contain multiplier on a fixed shared tag (oxytocin/
        # cortisol/trust/anguish). Superseded the
        # personalization now happens directly in the concept's own
        # push via compute_concept_push above, so no extra multiplier
        # step is needed for these two. Kept out of core_identity_rules
        # entirely (nothing left for it to do here).
    }

    # Optional identity data (only if answered).
    for _key, _field in (("father_name", "father"), ("mother_name", "mother"), ("pet_name", "pet")):
        if answers.get(_key):
            core_identity_rules["host_identity"]["value"][_field] = answers[_key]
    if answers.get("friend_name"):
        _friend = answers["friend_name"]
        core_identity_rules["custom_friend"] = {
            "type": "relationship", "concepts": ["friend", _friend.strip().lower()],
            "effect": "none", "factor": 1.0,
            "value": {"name": _friend, "role": "friend"},
            "note": ("Informational only, same as custom_fear/custom_comfort -- there is no "
                     "speaker-based trust mechanism yet (see phrase_builder.py _TRUST_MODES: "
                     "sharing personal info is gated by the CURRENT MODE, not by who is asking). "
                     "Added for narrative/manual reference."),
        }

    def _existing_type(word):
        """FIX 2026-09-19: core_fear/core_comfort always used the type
        "subject" and overwrote the original type of concepts already defined
        in db_concepts (e.g. "ghost": illogical -> subject). Same bug as the
        2026-09-12 fix in _add_valenced_concept; here the existing type is
        kept and "subject" is only used if the word is new."""
        import lexicon_db.db_concepts as _dbc
        return _dbc.CONCEPTS.get(word, {}).get("type", "subject")

    def _lookup_biological(word):
        """node_type from the (now-fixed, §21) lexicon, when the word is
        in it. Defaults to non-biological/object if unknown -- a
        conservative default, since most free-text fear/comfort words
        will be objects/situations rather than people."""
        node = LEXICON.get(word)
        return bool(node and node["node_type"] == "biological")

    if answers.get("core_fear"):
        fear_word = answers["core_fear"].strip().lower()
        # NOTE: resolve_concept() matches single tokens only -- a
        # multi-word phrase here will never match any input token.
        # Works correctly for a single evocative word (e.g.
        # "abandonment"); a phrase needs its own design (still open).
        _add_valenced_concept(fear_word, CORE_FEAR_VALUE, "internal",
                               "emotional", [fear_word],
                               biological=_lookup_biological(fear_word),
                               concept_type=_existing_type(fear_word))
        core_identity_rules["custom_fear"] = {
            "type": "fear", "concepts": [fear_word],
            "effect": "none", "factor": 1.0,
            "note": "Free-text fear — push computed via valence.py, this entry is informational only.",
        }

    if answers.get("core_comfort"):
        comfort_word = answers["core_comfort"].strip().lower()
        _add_valenced_concept(comfort_word, CORE_COMFORT_VALUE, "internal",
                               "emotional", [comfort_word],
                               biological=_lookup_biological(comfort_word),
                               concept_type=_existing_type(comfort_word))
        core_identity_rules["custom_comfort"] = {
            "type": "relief", "concepts": [comfort_word],
            "effect": "none", "factor": 1.0,
            "note": "Free-text comfort — push computed via valence.py, this entry is informational only.",
        }

    # ── IDENTITY ANCHORS ──────────────────────────────────────────────
    # Unlike core_fear/core_comfort (which give a general emotional load
    # via valence.py), these words don't need their own push -- they only
    # need to be a RECOGNIZABLE concept (resolve_concept() has to find
    # them) so that IdentityAnchorSystem (core_identity.py) can detect
    # them in concept_names every cycle. If the word doesn't already exist
    # in the lexicon, it is added as a neutral concept (no "related" --
    # the push comes from the anchor system, not the general tag system).
    identity_anchors = []
    _ANCHOR_QUESTIONS = [
        ("purpose_source",  "purpose"),
        ("security_source", "security"),
        ("valued_bond",     "company"),
        ("structure_source","structure"),
    ]
    for question_key, target_stat in _ANCHOR_QUESTIONS:
        raw = answers.get(question_key)
        if not raw:
            continue
        word = raw.strip().lower()
        if word not in concepts_seed and word not in LEXICON:
            concepts_seed[word] = {
                "sense": "internal", "type": "subject", "subtype": "anchor",
                "synonyms": [word], "related": {},
            }
        identity_anchors.append({"concept": word, "target_stat": target_stat})

    # ── World/likes tree (character/tree_questionnaire.py) ──────────────
    # Additive, not a replacement: covers every word tools/expand_category.py
    # resolved (~867 words / 27 nodes) that the hand-picked concepts above
    # can't reach (those cover a handful of specific hand-authored concepts;
    # this covers everything WordNet-anchored). No overlap in practice —
    # merge is a plain dict update, tree answers never override a
    # hand-picked concept sharing the exact same word.
    tree_concepts_seed, tree_tag_values_seed = populate_tree_concepts(answers, fortitude_1_10)
    for name, node in tree_concepts_seed.items():
        concepts_seed.setdefault(name, node)
    for tag, vec in tree_tag_values_seed["somatic"].items():
        tag_values_seed["somatic"].setdefault(tag, vec)
    for tag, vec in tree_tag_values_seed["mental"].items():
        tag_values_seed["mental"].setdefault(tag, vec)

    # "related" compiler prototype (§23) — same value + shared branch.
    # Only touches words the tree above already populated.
    for word, extra_keys in compile_related(answers).items():
        if word in concepts_seed:
            concepts_seed[word]["related"].update(extra_keys)

    return {
        "schema_version": "unique_host_v3_valence",
        "identity": {
            "name":   answers.get("name", "Unnamed"),
            "age":    answers.get("age", 25),
            "height": f"{answers.get('height_cm', 165)}cm",
            "physical_traits": answers.get("physical_traits", ""),
        },
        "core_identity_rules": core_identity_rules,
        "identity_anchors": identity_anchors,
        "concepts_seed": concepts_seed,
        "tag_values_seed": tag_values_seed,
        "base_state": {
            "somatic": {"V": V_base, "I": I_base, "Lv": Lv_base, "Gv": Gv_base},
            "mental":  {"P": P_base, "A": A_base, "Er": Er_base, "Rr": Rr_base},
        },
        "category_bias":  category_bias,
        "chemical_gains": chemical_gains,
        "mental_category_bias": mental_category_bias,
        "mental_gains":         mental_gains,
        "saturation_thresholds": {
            "mental_high":  mental_high,
            "somatic_high": somatic_high,
        },
    }
