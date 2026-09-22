# db/db_sounds.py — CCM v8
#
# REAL pre-verbal vocalization (original CCM doc 4.14: "Pre-verbal Vocal
# Output: when inference depth = 0, verbal output is replaced by
# unstructured affective vocalizations encoding somatic state through
# pitch, intensity, and duration"). Before, this was a bracket
# placeholder ("[tense]", "[breaking down]"). Now it maps the dominant
# SOMATIC mode (of the same 16 in systems/chemical_system.py:
# MATRIX_MODES) to a real sound, scaled by intensity/tension.
#
# Mechanism (unchanged, it already existed in layers/processing_mode.py):
# the SOMATIC verbal channel is activated when the mental engine saturates
# (inference_depth reaches 0, "preverbal") and the somatic engine dominates
# by euclidean distance -- that is when get_somatic_sound runs
# instead of an assembled sentence. This file only decides WHICH sound, not
# WHEN it is used.
#
# Design (adjustable -- any row can be tuned):
#   base: the core of the sound at medium intensity
#   low: muted/short version (just starting, low level)
#   high: intense/long version (high level, saturates)
# The duration/repetition of vowels ("a" -> "aaaa" -> "AAAAA") is the
# way to convey intensity without needing real audio.
#
# Real sources used to calibrate this table:
#   - Cowen & Keltner, vocal bursts (UC Berkeley, American Psychologist,
#     2019): mapping of >2,000 real vocal bursts to 24 recognizable
#     emotion categories -- full list below in COWEN_24_EMOTIONS,
#     with a note on which of the 16 modes each one was assigned to.
#     https://news.berkeley.edu/2019/02/04/audio-map-of-exclamations/
#   - Ohala's "frequency code": low/deep pitch = dominance, threat,
#     confidence; high pitch = submission, fear, uncertainty.
#   - Sound symbolism: /i/ (front vowel) = positive valence; /o/ and
#     rounded vowels = negative valence; nasals (/m/,/n/) =
#     roundness/warmth (bouba-kiki effect).

# The 24 real categories of Cowen & Keltner (2019), and which mode of
# the 16 each one was assigned to (several share a mode -- there are 24
# emotions over only 16 slots, some are variants of the
# same basic reaction). "—" = none of the 24 fits well; that mode
# is more a behavioral disposition (protect) or an internal process
# (formulate already took "realization") than a pure emotion.
COWEN_24_EMOTIONS = {
    "anger":              "attack",
    "fear":               "flee",             # scream
    "distress":           "surrender",
    "sadness":            "surrender",
    "ecstasy":            "accept",
    "elation":            "accept",
    "triumph":            "accept",           # alternate -- victory/achievement
    "amusement":          "accept",           # alternate -- laughter
    "contempt":           "deny",
    "disgust":            "deny",             # alternate
    "sympathy":           "cooperate",
    "adoration":          "cooperate",        # alternate (original source of core_comfort, not from Cowen -- see note)
    "desire":             "cooperate",        # alternate
    "contentment":        "ignore_benefit",
    "relief":             "ignore_benefit",
    "interest":           "observe",          # "ah?"
    "confusion":          "desist",           # "huh?" -- gives up trying to understand
    "disappointment":     "desist",
    "awe":                "investigate",      # "woah" -- your example
    "surprise_positive":  "investigate",      # alternate -- "gasp" of amazement
    "surprise_negative":  "signal",           # alternate -- "gasp" of alarm
    "realization":        "formulate",        # "ohhh"
    "pain":               "suppress",
    "embarrassment":      "suppress",         # alternate -- self-consciousness, restrained
    # no real Cowen match: "protect" (defensive posture, not an
    # emotion from the list) and "group"/"ignore_neutral" (low-intensity
    # contentment, they share with ignore_benefit).
}

MODE_SOUNDS = {
    # ── DANGER ───────────────────────────────────────────────────────
    "attack":    {"low": "grr",        "base": "GRAAH",       "high": "GRAAAAAH!!"},   # anger
    "surrender": {"low": "...uh",      "base": "uuhh...",     "high": "nnnnnhh..."},   # distress/sadness
    "protect":   {"low": "agh",        "base": "Aaaaaaaaaaaagggggggggh!", "high": "GRAAAAAAAHHHHHHHH!"},   # (no Cowen match -- posture, not emotion; author's own sound)
    "flee":      {"low": "eh",         "base": "eeh!",        "high": "EEEEHH!!"},     # fear (scream)

    # ── BENEFIT ──────────────────────────────────────────────────────
    "accept":         {"low": "ah",    "base": "aaah~",       "high": "AAAAH~!"},      # ecstasy/elation/triumph/amusement
    "deny":           {"low": "mh",    "base": "mh.",         "high": "MH!"},          # contempt/disgust
    "cooperate":      {"low": "mm",    "base": "mmm~",        "high": "MMMM~"},        # sympathy/adoration/desire
    "ignore_benefit": {"low": "ah",    "base": "ahh...",      "high": "aaahhh..."},     # contentment/relief

    # ── NEUTRAL ──────────────────────────────────────────────────────
    "observe":        {"low": "h?",    "base": "ah?",         "high": "AH?!"},         # interest
    "ignore_neutral": {"low": "nnh",   "base": "nnnhh",       "high": "NNNHHHH!"},     # contentment (low) -- author's own sound
    "group":          {"low": "mmh",   "base": "mmmhhhhhhh",  "high": "MMMHHHHHHH!"},  # contentment (low) -- author's own sound
    "formulate":      {"low": "oh.",   "base": "ohhh...",     "high": "OHHHH!"},       # realization

    # ── UNCLASSIFIABLE ───────────────────────────────────────────────
    "investigate": {"low": "oh?", "base": "oooh?",       "high": "OOOOH?!"},           # awe / surprise (positive)
    "desist":      {"low": "eh",  "base": "huh?",        "high": "huh?!"},             # confusion/disappointment
    "signal":      {"low": "oi",  "base": "hey!",        "high": "HEY!!"},             # surprise (negative) -- directed alarm
    "suppress":    {"low": "ks",  "base": "kss...",      "high": "KSSSS!"},            # pain/embarrassment (restrained)
}

_TENSION_TO_BAND = {
    "low":      "low",
    "medium":   "base",
    "high":     "high",
    "critical": "high",
}


def get_somatic_sound(mode_name: str, quadrant: str, tension: str) -> str:
    """
    mode_name : name of the mode with the highest level in chemicals.levels
                this cycle (attack/flee/protect/surrender/accept/deny/
                cooperate/ignore_benefit/observe/ignore_neutral/group/
                formulate/investigate/desist/signal/suppress). If no
                mode is active (all at 0), falls back to a generic
                neutral sound according to tension.
    tension   : "low"/"medium"/"high"/"critical" (get_tension_somatic())
    """
    sounds = MODE_SOUNDS.get(mode_name)
    if not sounds:
        # no active mode -- silence/simple breathing according to tension
        return {"low": "...", "medium": "...", "high": "hh...", "critical": "hhh!"}.get(tension, "...")

    band = _TENSION_TO_BAND.get(tension, "base")
    return sounds[band]
