# db/db_danger.py — UNIQUE HOST
#
# INTRINSIC DANGER TAGS for common roleplay words (bandit, monster, kill, blood, fire...).
#
# WHY IT EXISTS
# ─────────────
# CONCEPTS is a small hand-authored graph (~67 words with a real emotional push, "related").
# Every other word comes lazily from the lexicon with an EMPTY "related" (resolve_concept), so
# "kill", "blood", "monster", "fire" or "wounded" pushed nothing. In the tests
# "a monster kills her friend, blood is everywhere" was read as BENEFIT, a bandit with a drawn
# blade was welcomed, and the memory system had no inviability to store.
# On top of that, the character json's concepts_seed used to REPLACE hand-authored concepts
# (bandit lost its danger tags and got only the character's opinion of "people").
# character/injector.py now merges instead, so these tags survive a character seed and the
# character's own valence is layered on top.
#
# WHAT IT DOES
# ────────────
# TEMPLATES: "related" blocks in the same shape as db_concepts.py (group -> somatic/mental tags).
#             Only tags that already exist in db_somatic.py / db_mental.py are used
#             (tests/test_danger_tags.py checks it).
# DANGER_WORDS: template -> words. apply_danger(CONCEPTS) is called at the end of db_concepts.py:
#             - a word that already has a hand-authored "related" is NOT touched;
#             - a word already in CONCEPTS gets the template's "related";
#             - a word only in the lexicon is promoted like resolve_concept does, with the template;
#             - a word in neither gets a minimal node (FALLBACK_TYPE), so it is visible to the engine.
# It is a first draft of ~150 words to review and extend. Words with a dominant
# non-danger reading in roleplay (club, staff, spike, spell, scar, bear...) are deliberately left out.

TEMPLATES = {
    # hostile person: same shape as the hand-authored "bandit"
    "agent": {
        "fear":   {"somatic": ["adrenaline", "cortisol"],        "mental": ["seek_exit", "cognitive_threat"]},
        "threat": {"somatic": ["muscle_tension", "noradrenaline"], "mental": ["hypervigilance"]},
    },
    "creature": {
        "fear":   {"somatic": ["adrenaline", "cortisol"],        "mental": ["seek_exit", "cognitive_threat"]},
        "threat": {"somatic": ["muscle_tension", "noradrenaline"], "mental": ["hypervigilance"]},
        "danger": {"somatic": ["adrenaline", "flight_burst"],    "mental": ["traumatic_memory"]},
    },
    "weapon": {
        "threat":  {"somatic": ["muscle_tension", "noradrenaline"], "mental": ["hypervigilance"]},
        "hostile": {"somatic": ["hostile_contact"],                "mental": ["suspicion"]},
    },
    "violence": {
        "danger":  {"somatic": ["adrenaline", "flight_burst"],   "mental": ["traumatic_memory"]},
        "hostile": {"somatic": ["hostile_contact"],              "mental": ["terror"]},
        "fear":    {"somatic": ["adrenaline", "cortisol"],       "mental": ["seek_exit", "cognitive_threat"]},
    },
    "mortal": {
        "vital":   {"somatic": ["vital_threat", "death_presence"], "mental": ["mortality", "terror"]},
        "danger":  {"somatic": ["adrenaline", "flight_burst"],   "mental": ["traumatic_memory"]},
    },
    "injury": {
        "pain":    {"somatic": ["dolor", "adrenaline"],          "mental": ["anguish"]},
        "danger":  {"somatic": ["adrenaline"],                   "mental": ["traumatic_memory"]},
    },
    "hazard": {
        "danger":  {"somatic": ["adrenaline", "flight_burst"],   "mental": ["terror"]},
        "threat":  {"somatic": ["muscle_tension", "noradrenaline"], "mental": ["hypervigilance"]},
    },
    "fear_state": {
        "fear":        {"somatic": ["adrenaline", "cortisol"],   "mental": ["terror", "hypervigilance"]},
        "defenseless": {"somatic": ["paralysis"],                "mental": ["anguish"]},
    },
    "loss": {
        "isolated":    {"somatic": ["isolation"],                "mental": ["loneliness"]},
        "defenseless": {"somatic": ["cortisol"],                 "mental": ["anguish", "sadness"]},
    },
    "captivity": {
        "enclosed":    {"somatic": ["enclosed_space", "sofocacion"], "mental": ["anguish"]},
        "defenseless": {"somatic": ["paralysis"],                "mental": ["terror"]},
    },
}

DANGER_WORDS = {
    "agent": ["thief", "raider", "assassin", "killer", "murderer", "villain", "enemy", "outlaw", "intruder",
              "stalker", "kidnapper", "pirate", "mercenary", "tyrant", "executioner", "cultist", "warlord", "brute"],
    "creature": ["monster", "beast", "wolf", "dragon", "demon", "zombie", "vampire", "ogre", "goblin", "troll",
                 "serpent", "spider", "snake", "werewolf", "wraith", "undead", "predator", "shark", "scorpion"],
    "weapon": ["blade", "sword", "dagger", "knife", "axe", "spear", "arrow", "gun", "rifle", "pistol", "fang",
               "claw", "whip", "bomb", "cannon", "noose"],
    "violence": ["kill", "murder", "stab", "slash", "strike", "attack", "choke", "strangle", "torture", "ambush",
                 "assault", "lunge", "slaughter", "massacre", "execute", "betray", "threaten", "abduct", "punch",
                 "shoot", "hunt"],   # "beat" left out: "her heart beats" must not read as violence
    "mortal": ["die", "dying", "death", "dead", "doom", "perish"],
    "injury": ["hurt", "wound", "wounded", "bleed", "bleeding", "blood", "injury", "pain", "agony", "gore"],
    "hazard": ["fire", "flame", "flames", "smoke", "explosion", "poison", "venom", "storm", "flood", "avalanche",
               "earthquake", "plague", "drown", "collapse", "inferno", "lava", "blizzard", "burn"],
    "fear_state": ["afraid", "terrified", "terror", "panic", "horror", "scream", "dread", "frightened", "petrified",
                   "horrified"],
    "loss": ["lonely", "lost", "abandoned", "grief", "mourn", "betrayal", "hopeless", "despair", "orphan", "widow"],
    "captivity": ["cage", "prison", "dungeon", "chain", "chains", "captive", "trapped", "shackle"],
}

# type / subtype for a word that is in neither CONCEPTS nor the lexicon
FALLBACK_TYPE = {
    "agent": ("subject", "person"), "creature": ("subject", "animal"), "weapon": ("object", "weapon"),
    "violence": ("action", "action"), "mortal": ("status", "threat"), "injury": ("object", "injury"),
    "hazard": ("object", "hazard"), "fear_state": ("status", "emotion"), "loss": ("status", "social"),
    "captivity": ("object", "building"),
}


def _copy(related):
    return {g: {"somatic": list(b["somatic"]), "mental": list(b["mental"])} for g, b in related.items()}


def _inflections(word):
    """Other surface forms of `word` (kills, killed, killing, monsters...) via lemminflect.
    The engine does not lemmatise: "kills" is a different key from "kill", and without this the
    danger tags would only fire on the bare form. Returns [] if lemminflect is not installed."""
    try:
        from lemminflect import getAllInflections
    except Exception:
        return []
    forms = set()
    for pos_forms in getAllInflections(word).values():
        forms.update(pos_forms)
    forms.discard(word)
    return sorted(f for f in forms if len(f) > 2 and f.isalpha())


def apply_danger(concepts):
    """Adds the intrinsic danger tags to `concepts` (the CONCEPTS dict). Idempotent."""
    from db.db_lexicon import LEXICON
    try:
        from db.db_concepts import _NODE_TYPE_TO_CONCEPT_TYPE as node_map
    except Exception:                                   # called while db_concepts is still importing
        node_map = {}
    for template, words in DANGER_WORDS.items():
        for word in words:
            node = concepts.get(word)
            if node is not None and node.get("related"):
                continue                                # hand-authored: never overwritten
            if node is None:
                entry = LEXICON.get(word)
                if entry:
                    node = {"sense": None,
                            "type": node_map.get(entry.get("node_type"), FALLBACK_TYPE[template][0]),
                            "subtype": entry.get("category"),
                            "synonyms": list(entry.get("synonyms", [])),
                            "related": {}}
                else:
                    t, st = FALLBACK_TYPE[template]
                    node = {"sense": None, "type": t, "subtype": st, "synonyms": [word], "related": {}}
                concepts[word] = node
            node["related"] = _copy(TEMPLATES[template])
            node["intrinsic_danger"] = template
            # inflected forms get the same node (a copy), unless they already carry a hand-authored
            # push or are grammar words; a lexicon-promoted junk entry ("burns" = the person Burns) is replaced
            for form in _inflections(word):
                other = concepts.get(form)
                if other is not None and (other.get("related") or other.get("type") == "language"):
                    continue
                concepts[form] = {**node, "synonyms": [form], "related": _copy(TEMPLATES[template]),
                                  "intrinsic_danger": template, "inflection_of": word}
