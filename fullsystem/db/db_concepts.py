# db/db_concepts.py — CCM v5
#
# neural system — unified association graph
#
# Each node has:
#   sense    : sensory channel (sight, touch, hearing, smell, taste)
#   type     : category (illogical, subject, environment, object, status, action)
#   subtype  : subcategory placeholder
#   synonyms : alternative token forms
#   related  : dict child_node → {somatic: [...tags], mental: [...associations]}
#
# The related values flow down to the internal motors:
#   somatic → TAG_VALUES_SOMATIC tags (release chemicals, activate reflexes)
#   mental  → mental associations (search memory, evoke concepts)
#
# A node can have multiple parents (graph, not tree).
# The activation count is global — if adrenaline appears 3 times → x3.

CONCEPTS = {

    # ── ILLOGICAL ─────────────────────────────────────────────────────────────
    "ghost": {
        "sense":    "sight",
        "type":     "illogical",
        "subtype":  "apparition",
        "synonyms": ["spirit", "phantom", "specter", "apparition"],
        "related": {
            "self":         {"somatic": ["concept_ghost"],                   "mental": ["concept_ghost"]},
            "fear":         {"somatic": ["adrenaline", "cortisol"],          "mental": ["seek_light", "seek_person"]},
            "danger":       {"somatic": ["adrenaline", "flight_burst"],             "mental": ["traumatic_memory"]},
            "supernatural": {"somatic": [],                                  "mental": ["disbelief", "denial"]},
            "defenseless":  {"somatic": ["paralysis", "muscle_tension"],   "mental": ["seek_exit"]},
        }
    },
    "shadow": {
        "sense":    "sight",
        "type":     "illogical",
        "subtype":  "apparition",
        "synonyms": ["shade", "silhouette"],
        "related": {
            "fear":         {"somatic": ["muscle_tension"],                "mental": ["seek_light"]},
            "uncertainty":  {"somatic": ["noradrenaline"],                   "mental": ["confusion", "hypervigilance"]},
            "danger":       {"somatic": ["adrenaline"],                      "mental": ["cognitive_threat"]},
        }
    },
    "corpse": {
        "sense":    "sight",
        "type":     "illogical",
        "subtype":  "presence",
        "synonyms": ["body", "cadaver"],
        "related": {
            "death":        {"somatic": ["paralysis", "death_presence"],   "mental": ["mortality", "disbelief"]},
            "danger":       {"somatic": ["adrenaline"],                      "mental": ["cognitive_threat"]},
            "fear":         {"somatic": ["cortisol"],                        "mental": ["anguish"]},
        }
    },

    # ── SUBJECT ───────────────────────────────────────────────────────────────
    "person": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "person",
        "synonyms": ["someone", "people", "human"],
        "related": {
            "self":         {"somatic": ["concept_person"],                  "mental": ["concept_person"]},
            "safe":         {"somatic": ["oxytocin", "serotonin"],         "mental": ["seek_person", "trust"]},
            "trust":        {"somatic": ["oxytocin"],                       "mental": ["affection", "relief"]},
            "social":       {"somatic": ["serotonin"],                      "mental": ["relief"]},
        }
    },
    "animal": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "animal",
        "synonyms": ["beast", "creature"],
        "related": {
            "danger":       {"somatic": ["adrenaline", "muscle_tension"],  "mental": ["alert", "suspicion"]},
            "threat":       {"somatic": ["noradrenaline"],                   "mental": ["hypervigilance"]},
            "unpredictable":{"somatic": ["cortisol"],                        "mental": ["suspicion"]},
        }
    },

    # ── ENVIRONMENT ───────────────────────────────────────────────────────────
    "room": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "built",
        "synonyms": ["chamber"],
        "related": {
            "self":         {"somatic": ["concept_room"],                    "mental": ["concept_room"]},
            "enclosed":     {"somatic": ["enclosed_space"],                 "mental": ["anticipation", "loneliness"]},
            "isolated":     {"somatic": ["isolation"],                     "mental": ["loneliness"]},
            "dark":         {"somatic": ["physical_darkness"],                "mental": ["hypervigilance"]},
        }
    },
    "dark": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "condition",
        "synonyms": ["darkness", "dim"],
        "related": {
            "self":         {"somatic": ["concept_dark"],                    "mental": ["concept_dark"]},
            "fear":         {"somatic": ["cortisol", "noradrenaline"],       "mental": ["seek_light", "anguish"]},
            "danger":       {"somatic": ["muscle_tension"],                "mental": ["cognitive_threat"]},
            "uncertainty":  {"somatic": ["noradrenaline"],                   "mental": ["confusion", "hypervigilance"]},
            "defenseless":  {"somatic": ["muscle_tension"],                "mental": ["anguish"]},
        }
    },
    "light": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "condition",
        "synonyms": ["bright", "lamp"],
        "related": {
            "self":         {"somatic": ["concept_light"],                   "mental": ["concept_light"]},
            "safe":         {"somatic": ["serotonin", "ambient_light"],      "mental": ["relief", "clarity"]},
            "calm":         {"somatic": ["body_calm"],                    "mental": ["clarity"]},
            "warmth":       {"somatic": ["serotonin"],                      "mental": ["mental_security"]},
        }
    },
    "night": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "time",
        "synonyms": ["midnight", "evening"],
        "related": {
            "dark":         {"somatic": ["physical_darkness", "cortisol"],    "mental": ["hypervigilance"]},
            "fear":         {"somatic": ["noradrenaline"],                   "mental": ["anticipation"]},
            "uncertainty":  {"somatic": ["muscle_tension"],                "mental": ["confusion"]},
        }
    },
    "forest": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "natural",
        "synonyms": ["woods", "jungle"],
        "related": {
            "isolated":     {"somatic": ["isolation"],                     "mental": ["loneliness", "anticipation"]},
            "unpredictable":{"somatic": ["noradrenaline"],                   "mental": ["alert"]},
            "natural":      {"somatic": ["open_space"],                 "mental": ["curiosity"]},
        }
    },
    "house": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "built",
        "synonyms": ["home", "house"],
        "related": {
            "safe":         {"somatic": ["serotonin", "body_calm"],      "mental": ["mental_security", "relief"]},
            "calm":         {"somatic": ["body_calm"],                    "mental": ["acceptance"]},
            "trust":        {"somatic": ["oxytocin"],                       "mental": ["trust"]},
        }
    },
    "place": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "natural",
        "synonyms": ["spot", "site"],
        "related": {
            "enclosed":     {"somatic": ["enclosed_space"],                 "mental": ["anticipation"]},
            "isolated":     {"somatic": ["isolation"],                     "mental": ["loneliness"]},
        }
    },

    # ── SUBJECT / SOCIAL ──────────────────────────────────────────────────────
        # ── MUSIC ─────────────────────────────────────────────────────────────────
    "melody": {
        "sense":    "hearing",
        "type":     "music",
        "subtype":  "melodic_phrase",
        "synonyms": ["melody", "tune", "song", 
                     "music", "beautiful_song"],
        "related": {
            "calm":     {"somatic": ["soft_melody", "calm_rhythm"],  "mental": ["mental_melody", "contemplation"]},
            "warmth":   {"somatic": ["melodic_phrase"],                "mental": ["soft_resonance"]},
            "presence": {"somatic": ["calm_rhythm"],                   "mental": ["contemplation", "mental_melody"]},
        }
    },
    "angelo": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "person_known",
        "synonyms": ["angelo", "angel", "angelo-typo"],
        "related": {
            "love":     {"somatic": ["oxytocin", "safe_presence", "safe_contact"], "mental": ["affection", "trust", "relief"]},
            "admire":   {"somatic": ["serotonin", "muscle_calm"],                    "mental": ["trust", "mental_security", "clarity"]},
            "safe":     {"somatic": ["oxytocin", "body_calm"],                       "mental": ["mental_security", "relief"]},
            "social":   {"somatic": ["serotonin"],                                      "mental": ["affection", "joy"]},
        }
    },
"person": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "social",
        "synonyms": ["someone", "people", "human"],
        "related": {
            "safe":     {"somatic": ["oxytocin", "safe_presence"], "mental": ["trust", "security"]},
            "calm":     {"somatic": ["muscle_calm", "serotonin"],  "mental": ["relief", "clarity"]},
            "social":   {"somatic": ["serotonin"],                    "mental": ["cognitive_calm", "mental_clarity"]},
        }
    },
    "street": {
        "sense":    "sight",
        "type":     "environment",
        "subtype":  "outdoor",
        "synonyms": ["outside", "outdoor", "open"],
        "related": {
            "safe":     {"somatic": ["serotonin", "safe_presence"], "mental": ["security", "clarity"]},
            "open":     {"somatic": ["muscle_calm"],                 "mental": ["relief", "mental_clarity"]},
            "calm":     {"somatic": ["oxytocin"],                      "mental": ["cognitive_calm"]},
        }
    },

    # ── SUBJECT / ANIMALES ────────────────────────────────────────────────────
    "fish": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "animal",
        "synonyms": ["salmon"],
        "related": {
            "water":    {"somatic": [],               "mental": ["clarity"]},
            "calm":     {"somatic": ["body_calm"],  "mental": ["clarity"]},
            "natural":  {"somatic": ["open_space"],"mental": ["curiosity"]},
        }
    },
    "bird": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "animal",
        "synonyms": ["bird", "bird", "bird", "small-bird", "eagle", "dove"],
        "related": {
            "fly":      {"somatic": ["open_space"], "mental": ["clarity", "curiosity"]},
            "natural":  {"somatic": ["open_space"], "mental": ["curiosity"]},
            "calm":     {"somatic": ["body_calm"],    "mental": ["relief"]},
        }
    },
    "duck": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "animal",
        "synonyms": ["ducks", "anatidae"],
        "related": {
            "fly":      {"somatic": ["open_space"], "mental": ["curiosity"]},
            "natural":  {"somatic": ["open_space"], "mental": ["curiosity"]},
            "calm":     {"somatic": ["body_calm"],    "mental": ["clarity"]},
        }
    },

    # ── STATUS ────────────────────────────────────────────────────────────────
    # good/bad/mysterious added 2026-09-0X to test "X person asks your name"
    # scenarios — judgment-of-a-person words, same static/universal tier as
    # danger/safe/calm (see character/questionnaire.py's WORLD_GROUPS
    # comment for why these stay static rather than going through
    # character/valence.py: they're not "opinion of a thing", they're
    # reaction triggers). "bad" mirrors danger's tags exactly (same proven
    # attack/flee/surrender behavior); "good" mirrors safe's; "mysterious"
    # is new — it deliberately does NOT carry fear/threat tags, only the
    # new curiosity_pull tag (db/db_somatic.py, db/db_mental.py), so it
    # reads as unresolved/unclassifiable rather than as danger.
    "good": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "judgment",
        "synonyms": ["good", "kind", "nice", "trustworthy", "benevolent"],
        "related": {
            "calm":  {"somatic": ["serotonin", "body_calm"], "mental": ["relief", "clarity"]},
            "trust": {"somatic": ["oxytocin"],                "mental": ["trust", "mental_security"]},
        }
    },
    "bad": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "judgment",
        "synonyms": ["bad", "evil", "malicious", "untrustworthy", "cruel", "wicked"],
        "related": {
            "fear":   {"somatic": ["adrenaline", "cortisol"],           "mental": ["seek_exit", "cognitive_threat"]},
            "threat": {"somatic": ["muscle_tension", "noradrenaline"],  "mental": ["hypervigilance"]},
        }
    },
    "mysterious": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "judgment",
        "synonyms": ["mysterious", "strange", "odd", "enigmatic", "unknown", "uncanny", "cryptic"],
        "related": {
            "curiosity": {"somatic": ["curiosity_pull"], "mental": ["curiosity_pull"]},
        }
    },
    # roleplay archetypes — same static/universal tier as
    # good/bad/danger/safe above, not personalized valence: "a bandit" is
    # inherently a threat-type encounter regardless of who's asking,
    # same reasoning as danger/safe staying static (see WORLD_GROUPS
    # comment in character/questionnaire.py). Reuse bad's/good's exact
    # tags rather than inventing new ones -- these ARE the same
    # reaction, just a more specific trigger word for it.
    "bandit": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "person",
        "synonyms": ["bandit", "brigand", "outlaw", "highwayman", "raider", "cutthroat"],
        "related": {
            "fear":   {"somatic": ["adrenaline", "cortisol"],           "mental": ["seek_exit", "cognitive_threat"]},
            "threat": {"somatic": ["muscle_tension", "noradrenaline"],  "mental": ["hypervigilance"]},
        }
    },
    "villain": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "person",
        "synonyms": ["villain", "scoundrel", "rogue", "thief", "assassin", "mercenary"],
        "related": {
            "fear":   {"somatic": ["adrenaline", "cortisol"],           "mental": ["seek_exit", "cognitive_threat"]},
            "threat": {"somatic": ["muscle_tension", "noradrenaline"],  "mental": ["hypervigilance"]},
        }
    },
    "hero": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "person",
        "synonyms": ["hero", "adventurer", "knight", "protector", "champion"],
        "related": {
            "calm":  {"somatic": ["serotonin", "body_calm"], "mental": ["relief", "clarity"]},
            "trust": {"somatic": ["oxytocin"],                "mental": ["trust", "mental_security"]},
        }
    },
    "danger": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "threat",
        "synonyms": ["dangerous"],
        "related": {
            "fear":         {"somatic": ["adrenaline", "cortisol"],          "mental": ["seek_exit", "cognitive_threat"]},
            "threat":       {"somatic": ["muscle_tension", "noradrenaline"],"mental": ["hypervigilance"]},
            "defenseless":  {"somatic": ["paralysis"],                       "mental": ["denial"]},
            "run":          {"somatic": ["adrenaline", "flight_burst"],             "mental": ["seek_exit"]},
        }
    },
    "threat": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "threat",
        "synonyms": ["threatening"],
        "related": {
            "danger":       {"somatic": ["adrenaline", "noradrenaline"],     "mental": ["cognitive_threat"]},
            "fear":         {"somatic": ["cortisol"],                        "mental": ["hypervigilance"]},
            "defenseless":  {"somatic": ["muscle_tension"],                "mental": ["denial"]},
        }
    },
    "alone": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "social",
        "synonyms": ["alone", "lonely", "solitary"],
        "related": {
            "isolated":     {"somatic": ["isolation"],                     "mental": ["loneliness"]},
            "defenseless":  {"somatic": ["cortisol"],                        "mental": ["anguish"]},
            "fear":         {"somatic": ["noradrenaline"],                   "mental": ["anticipation"]},
        }
    },
    "safe": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "safety",
        "synonyms": ["protected", "secure"],
        "related": {
            "calm":         {"somatic": ["serotonin", "body_calm"],      "mental": ["relief", "clarity"]},
            "trust":        {"somatic": ["oxytocin"],                       "mental": ["trust", "mental_security"]},
            "warmth":       {"somatic": ["serotonin"],                      "mental": ["acceptance"]},
        }
    },
    "calm": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "emotional",
        "synonyms": ["peaceful", "relaxed"],
        "related": {
            "safe":         {"somatic": ["serotonin", "body_calm"],      "mental": ["clarity", "acceptance"]},
            "trust":        {"somatic": ["oxytocin"],                       "mental": ["trust"]},
            "warmth":       {"somatic": ["body_calm"],                    "mental": ["relief"]},
        }
    },
    "scared": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "emotional",
        "synonyms": ["afraid", "frightened", "terrified"],
        "related": {
            "fear":         {"somatic": ["adrenaline", "cortisol"],          "mental": ["seek_exit", "cognitive_threat"]},
            "danger":       {"somatic": ["adrenaline"],                      "mental": ["seek_person"]},
            "defenseless":  {"somatic": ["paralysis"],                       "mental": ["denial", "overflow"]},
            "run":          {"somatic": ["flight_burst", "adrenaline"],             "mental": ["seek_exit"]},
        }
    },
    "tired": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "physical",
        "synonyms": ["exhausted", "weary"],
        "related": {
            "defenseless":  {"somatic": ["fatigue", "immobility"],           "mental": ["denial"]},
            "isolated":     {"somatic": ["isolation"],                     "mental": ["loneliness"]},
        }
    },
    "quiet": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "condition",
        "synonyms": ["silence", "silent", "still"],
        "related": {
            "calm":         {"somatic": ["silence", "body_calm"],        "mental": ["clarity"]},
            "safe":         {"somatic": ["body_calm"],                    "mental": ["acceptance"]},
        }
    },

    # ── ACTION ────────────────────────────────────────────────────────────────
    "run": {
        "sense":    "sight",
        "type":     "action",
        "subtype":  "locomotion",
        "synonyms": ["flee", "escape"],
        "related": {
            "fear":         {"somatic": ["adrenaline", "flight_burst"],             "mental": ["seek_exit"]},
            "danger":       {"somatic": ["adrenaline", "fast_movement"], "mental": ["cognitive_threat"]},
            "escape":       {"somatic": ["endorphins", "flight_burst"],             "mental": ["seek_exit"]},
        }
    },
    "walk": {
        "sense":    "sight",
        "type":     "action",
        "subtype":  "locomotion",
        "synonyms": ["stroll", "march"],
        "related": {
            "calm":         {"somatic": ["slow_movement", "serotonin"],  "mental": ["clarity"]},
            "safe":         {"somatic": ["firm_surface"],                "mental": ["acceptance"]},
        }
    },
    "hide": {
        "sense":    "sight",
        "type":     "action",
        "subtype":  "evasion",
        "synonyms": ["conceal", "crouch"],
        "related": {
            "fear":         {"somatic": ["cortisol", "immobility"],         "mental": ["seek_exit", "denial"]},
            "danger":       {"somatic": ["muscle_tension"],                "mental": ["cognitive_threat"]},
            "enclosed":     {"somatic": ["enclosed_space"],                 "mental": ["anticipation"]},
            "defenseless":  {"somatic": ["paralysis"],                       "mental": ["denial"]},
        }
    },
    "breathe": {
        "sense":    "sight",
        "type":     "action",
        "subtype":  "physiological",
        "synonyms": ["inhale", "exhale"],
        "related": {
            "calm":         {"somatic": ["breathing", "body_calm"],     "mental": ["clarity", "relief"]},
            "safe":         {"somatic": ["serotonin"],                      "mental": ["acceptance"]},
        }
    },

    # ── ACTION / LOCOMOCION ───────────────────────────────────────────────────
    "fly": {
        "sense":    "sight",
        "type":     "action",
        "subtype":  "locomotion",
        "synonyms": ["flies", "flying"],
        "related": {
            "freedom":  {"somatic": ["open_space"], "mental": ["clarity", "curiosity"]},
            "natural":  {"somatic": [],                  "mental": ["clarity"]},
        }
    },

    # ── OBJECT ────────────────────────────────────────────────────────────────
    "food": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "consumable",
        "synonyms": ["meal", "eat"],
        "related": {
            "safe":         {"somatic": ["satiety", "dopamine"],            "mental": ["relief", "acceptance"]},
            "warmth":       {"somatic": ["serotonin"],                      "mental": ["clarity"]},
            "calm":         {"somatic": ["body_calm"],                    "mental": ["acceptance"]},
        }
    },
    "water": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "consumable",
        "synonyms": ["drink", "liquid"],
        "related": {
            "safe":         {"somatic": ["satiety", "body_calm"],        "mental": ["relief"]},
            "calm":         {"somatic": ["body_calm"],                    "mental": ["clarity"]},
        }
    },
    "money": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "resource",
        "synonyms": ["cash", "resource"],
        "related": {
            "safe":         {"somatic": ["dopamine"],                        "mental": ["trust", "clarity"]},
            "trust":        {"somatic": ["serotonin"],                      "mental": ["mental_security"]},
        }
    },
    "keys": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "tool",
        "synonyms": ["keys", "key"],
        "related": {
            "enclosed":     {"somatic": ["muscle_tension"],                "mental": ["anticipation"]},
            "escape":       {"somatic": ["adrenaline"],                      "mental": ["seek_exit"]},
            "safe":         {"somatic": ["dopamine"],                        "mental": ["relief"]},
        }
    },
    "door": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "structure",
        "synonyms": ["gate", "entrance"],
        "related": {
            "enclosed":     {"somatic": ["enclosed_space"],                 "mental": ["anticipation"]},
            "escape":       {"somatic": ["adrenaline"],                      "mental": ["seek_exit"]},
            "safe":         {"somatic": ["firm_surface"],                "mental": ["relief"]},
        }
    },
    "window": {
        "sense":    "sight",
        "type":     "object",
        "subtype":  "structure",
        "synonyms": ["glass", "pane"],
        "related": {
            "light":        {"somatic": ["ambient_light"],                    "mental": ["clarity"]},
            "escape":       {"somatic": ["adrenaline"],                      "mental": ["seek_exit"]},
            "safe":         {"somatic": ["body_calm"],                    "mental": ["relief"]},
        }
    },
    # ── HEARING / LANGUAGE → mental only ─────────────────────────────────────
    "kind": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["friendly", "kind", "gentle", "cordial"],
        "related": {
            "safe":         {"somatic": [],                                  "mental": ["trust", "relief"]},
            "trust":        {"somatic": [],                                  "mental": ["affection", "mental_security"]},
            "calm":         {"somatic": [],                                  "mental": ["clarity", "acceptance"]},
        }
    },
    "cold_tone": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["cold", "distant", "inexpressive", "flat"],
        "related": {
            "uncertainty":  {"somatic": [],                                  "mental": ["suspicion", "confusion"]},
            "alone":        {"somatic": [],                                  "mental": ["loneliness", "anticipation"]},
        }
    },
    "angry": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["angry", "furious", "aggressive"],
        "related": {
            "threat":       {"somatic": [],                                  "mental": ["cognitive_threat", "hypervigilance"]},
            "danger":       {"somatic": [],                                  "mental": ["anguish", "seek_exit"]},
            "fear":         {"somatic": [],                                  "mental": ["seek_person", "denial"]},
        }
    },
    "sad_tone": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["sad", "melancholic"],
        "related": {
            "alone":        {"somatic": [],                                  "mental": ["loneliness", "sadness"]},
            "uncertainty":  {"somatic": [],                                  "mental": ["confusion", "anguish"]},
        }
    },
    "urgent": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["urgent", "alarmed"],
        "related": {
            "danger":       {"somatic": [],                                  "mental": ["cognitive_threat", "seek_exit"]},
            "fear":         {"somatic": [],                                  "mental": ["hypervigilance", "anticipation"]},
        }
    },
    "neutral_tone": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "voice_tone",
        "synonyms": ["neutral", "calm_voice", "monotone"],
        "related": {
            "calm":         {"somatic": [],                                  "mental": ["clarity", "acceptance"]},
        }
    },

    # ── HEARING / TONE → mental + somatic ──────────────────────────────────────
    # Physical tone (dB, Hz) goes through db_receptors to the somatic cycle.
    # Here the semantic category for the mental engine is defined.
    "scream": {
        "sense":    "hearing",
        "type":     "tone",
        "subtype":  "volume",
        "synonyms": ["scream", "shout", "yell"],
        "related": {
            "danger":       {"somatic": ["adrenaline", "muscle_tension"],  "mental": ["cognitive_threat", "seek_exit"]},
            "fear":         {"somatic": ["cortisol", "noradrenaline"],       "mental": ["hypervigilance", "anguish"]},
            "threat":       {"somatic": ["adrenaline"],                      "mental": ["seek_person"]},
        }
    },
    "whisper": {
        "sense":    "hearing",
        "type":     "tone",
        "subtype":  "volume",
        "synonyms": ["whisper", "murmur"],
        "related": {
            "uncertainty":  {"somatic": ["noradrenaline"],                   "mental": ["suspicion", "hypervigilance"]},
            "fear":         {"somatic": ["muscle_tension"],                "mental": ["anticipation"]},
        }
    },
    "auditory_silence": {
        "sense":    "hearing",
        "type":     "tone",
        "subtype":  "volume",
        "synonyms": ["silence", "quiet_sound", "no_sound"],
        "related": {
            "calm":         {"somatic": ["silence", "body_calm"],        "mental": ["clarity"]},
            "uncertainty":  {"somatic": ["noradrenaline"],                   "mental": ["anticipation", "suspicion"]},
        }
    },

    # ── LANGUAGE / question ───────────────────────────────────────────────
    # Negative value — a question opens momentary absence (A rises, P falls)
    # The system searches for a response to close that opening
    "which": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "question_word",
        "synonyms": ["what", "which", "what-is"],
        "related": {
            "uncertainty":  {"somatic": [],  "mental": ["confusion", "anticipation"]},
            "search":       {"somatic": [],  "mental": ["seek_exit", "clarity"]},
        }
    },
    "who": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "question_word",
        "synonyms": ["who"],
        "related": {
            "uncertainty":  {"somatic": [],  "mental": ["suspicion", "anticipation"]},
            "search":       {"somatic": [],  "mental": ["seek_person"]},
        }
    },
    "where": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "question_word",
        "synonyms": ["where"],
        "related": {
            "uncertainty":  {"somatic": [],  "mental": ["confusion", "anticipation"]},
            "search":       {"somatic": [],  "mental": ["seek_exit"]},
        }
    },
    "how_question": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "question_word",
        "synonyms": ["how"],
        "related": {
            "uncertainty":  {"somatic": [],  "mental": ["confusion", "clarity"]},
        }
    },

    # ── LANGUAGE / subject ─────────────────────────────────────────────────────
    "self": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "internal_subject",
        "synonyms": ["i", "me", "myself", "i'm", "im"],
        "related": {
            "identity":    {"somatic": [],  "mental": ["mental_security", "clarity"]},
            "name":       {"somatic": [],  "mental": ["clarity"]},
        }
    },
    "you": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "external_subject",
        "synonyms": ["you", "your", "yours"],
        "related": {
            "identity":    {"somatic": [],  "mental": ["anticipation", "clarity"]},
            "social":       {"somatic": [],  "mental": ["seek_person"]},
        }
    },

    # ── LANGUAGE / VERB ───────────────────────────────────────────────────────
    "be": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "verb",
        "synonyms": ["am", "is", "are", "be", "called"],
        "related": {
            "identity":    {"somatic": [],  "mental": ["clarity", "acceptance"]},
        }
    },

    # ── LANGUAGE / property ──────────────────────────────────────────────────
    "name": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "property",
        "synonyms": ["name", "called", "julia"],
        "related": {
            "identity":    {"somatic": [],  "mental": ["clarity", "mental_security"]},
            "name":       {"somatic": [],  "mental": ["clarity"]},
        }
    },
    "identity": {
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "property",
        "synonyms": ["identity", "who are you", "who am i"],
        "related": {
            "identity":    {"somatic": [],  "mental": ["clarity", "mental_security"]},
        }
    },
    "father": {
        # added to test the identity system past just
        # "name" -- resolve_concept needs a token to map to before
        # any property lookup can even be attempted. "dad"/"papa" as
        # synonyms so casual phrasing resolves the same way.
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "property",
        "synonyms": ["father", "dad", "papa"],
        "related": {
            "identity": {"somatic": [],  "mental": ["clarity"]},
            "family":   {"somatic": [],  "mental": ["nostalgia", "clarity"]},
        }
    },
    "mother": {
        # added alongside "father" -- same reasoning,
        # same shape. "mom"/"mama" as synonyms.
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "property",
        "synonyms": ["mother", "mom", "mama"],
        "related": {
            "identity": {"somatic": [],  "mental": ["clarity"]},
            "family":   {"somatic": [],  "mental": ["nostalgia", "clarity"]},
        }
    },
    "pet": {
        # same reasoning as "father" above.
        "sense":    "hearing",
        "type":     "language",
        "subtype":  "property",
        "synonyms": ["pet", "dog", "cat", "companion animal"],
        "related": {
            "identity": {"somatic": [],  "mental": ["clarity"]},
            "affection": {"somatic": [], "mental": ["warmth", "clarity"]},
        }
    },

    "aggressive": {
        "sense":    "sight",
        "type":     "status",
        "subtype":  "threat",
        "synonyms": ["aggression", "hostile", "violent"],
        "related": {
            "danger":      {"somatic": ["adrenaline", "noradrenaline", "muscle_tension"], "mental": ["cognitive_threat", "hypervigilance"]},
            "fear":        {"somatic": ["cortisol", "adrenaline"],                          "mental": ["hypervigilance", "anguish"]},
            "threat":      {"somatic": ["muscle_tension", "noradrenaline"],               "mental": ["cognitive_threat", "denial"]},
            "defenseless": {"somatic": ["paralysis"],                                        "mental": ["seek_exit"]},
        },
    },

    "face": {
        "sense":    "sight",
        "type":     "subject",
        "subtype":  "social",
        "synonyms": ["face_alt", "expression"],
        "related": {
            "social":  {"somatic": ["serotonin"],       "mental": ["cognitive_calm"]},
            "threat":  {"somatic": ["muscle_tension"], "mental": ["hypervigilance"]},
            "fear":    {"somatic": ["cortisol"],         "mental": ["cognitive_threat"]},
        },
    },

    "tone": {
        "sense":    "hearing",
        "type":     "status",
        "subtype":  "social",
        "synonyms": ["voice", "tones"],
        "related": {
            "threat":  {"somatic": ["noradrenaline", "muscle_tension"], "mental": ["hypervigilance", "cognitive_threat"]},
            "social":  {"somatic": ["serotonin"],                        "mental": ["cognitive_calm"]},
        },
    },

}


# ── RESOLVERS ─────────────────────────────────────────────────────────────────

# node_type (db/db_lexicon.py, from tools/generate_lexicon.py) -> the
# same 4-way split CONCEPTS' own "type" field uses for subject/action
# classification (biological=Subject/North, non_biological=Object/South,
# action=Sensorial/East, quality=Structural/West -- confirmed
# , see tools/generate_lexicon.py's module docstring).
_NODE_TYPE_TO_CONCEPT_TYPE = {
    "biological":     "subject",
    "non_biological": "object",
    "action":         "action",
    "quality":        "quality",
}


def resolve_concept(token):
    """Resolves raw token → canonical name in CONCEPTS.

    FALLBACK TO LEXICON (2026-09-12): CONCEPTS is a small hand-curated
    graph (~300 words with real emotional "related" pushes) -- it only
    had 5 "action"-type entries in the whole system (run/walk/hide/
    breathe/fly), so verbs like "attack"/"cast"/"burn" were silently
    invisible to the concept pipeline (and therefore to memory) even
    though they've been sitting in db/db_lexicon.py's 5000+ words the
    whole time, correctly tagged via node_type. A token not found in
    CONCEPTS now falls back to LEXICON: if it's there, it gets lazily
    promoted into CONCEPTS with type/subtype/synonyms taken from its
    lexicon entry (mapped through _NODE_TYPE_TO_CONCEPT_TYPE) and an
    EMPTY "related" (no emotional push -- it was never hand-authored
    one, this only makes it visible/classifiable, not emotionally
    active). This means get_focus()'s PRIORITY list and memory's
    subject/action/environment split can now actually see actions and
    qualities from the big lexicon, not just the curated 300.
    """
    token = token.lower().strip()
    if token in CONCEPTS:
        return token
    for name, c in CONCEPTS.items():
        if token in [s.lower() for s in c.get("synonyms", [])]:
            return name

    from db.db_lexicon import LEXICON
    entry = LEXICON.get(token)
    if entry:
        concept_type = _NODE_TYPE_TO_CONCEPT_TYPE.get(entry.get("node_type"), "object")
        CONCEPTS[token] = {
            "sense":    None,
            "type":     concept_type,
            "subtype":  entry.get("category"),
            "synonyms": entry.get("synonyms", []),
            "related":  {},
        }
        return token

    return None


def get_internal_activations(concept_names):
    """
    Given a list of scene concepts, returns:
      somatic_counts: {tag: count}  — how many times each somatic tag activates
      mental_counts:  {assoc: count} — how many times each mental association activates
    The multiplier of each activation = count (release x1, x2, x3...)
    """
    from collections import Counter
    somatic_counts = Counter()
    mental_counts  = Counter()

    for name in concept_names:
        c = CONCEPTS.get(name, {})
        for related_node, branches in c.get("related", {}).items():
            for tag in branches.get("somatic", []):
                somatic_counts[tag] += 1
            for assoc in branches.get("mental", []):
                mental_counts[assoc] += 1

    return dict(somatic_counts), dict(mental_counts)


def get_focus(concept_names):
    """Returns the highest-priority concept (focus) from the scene."""
    PRIORITY = ["illogical", "subject", "action", "status", "environment", "object", "quality"]
    STATUS_SUB = ["threat", "emotional", "physical", "social", "safety", "condition"]

    best_name, best_score = None, (999, 999)
    for name in concept_names:
        c = CONCEPTS.get(name, {})
        ctype   = c.get("type", "object")
        subtype = c.get("subtype", "")
        ts = PRIORITY.index(ctype) if ctype in PRIORITY else 999
        ss = STATUS_SUB.index(subtype) if (ctype == "status" and subtype in STATUS_SUB) else 999
        if (ts, ss) < best_score:
            best_score = (ts, ss)
            best_name  = name
    return best_name


def get_multiplier(focus_name, concept_names):
    """
    Counts related matches between the focus and the other concepts.
    Multiplicador = coincidencias + 1
    """
    focus = CONCEPTS.get(focus_name, {})
    focus_related = set(focus.get("related", {}).keys())
    if not focus_related:
        return 1

    coincidences = 0
    for name in concept_names:
        if name == focus_name:
            continue
        other_related = set(CONCEPTS.get(name, {}).get("related", {}).keys())
        coincidences += len(focus_related & other_related)

    return coincidences + 1


# ── Intrinsic danger tags (roleplay words) — see db/db_danger.py ─────────────
# Called at the END of this module so it does not touch the hand-authored graph above:
# words that already carry a "related" are left alone.
from db.db_danger import apply_danger as _apply_danger
_apply_danger(CONCEPTS)
