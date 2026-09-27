# core/loss_safety_net.py — UNIQUE HOST
#
# MINIMAL WORDING GUARD for a known wording hole.
# This is NOT option A/B/C from that draft. It does not touch which mode wins, the emotion label, memory,
# or valence -- a loss scene still resolves on the character's own dominant axis, exactly as today, and can
# still read as an odd or overly composed reaction. This module only stops the specific failure that reads
# as a LANGUAGE error rather than a personality quirk: "attack"/"accept" are rendered as literal physical or
# social gestures (attacking, tearing into, thanking, welcoming...) and that reads as nonsense -- not "in
# character" -- when the target is a feeling ("we attack the grief") or something just lost/destroyed/stolen
# ("thanking the home" right after it burned down).
#
# Scope, on purpose: only the two mode families actually observed producing nonsense wording (attack,
# accept). Other modes on a loss scene (investigate, suppress, signal, observe...) can still read as cold
# or detached ("we take a look at the mother, quietly") -- that is a character/axis question for option
# A/B/C, not a language error, and is left alone here.
# Known gap: the emotion label (a separate lookup, keyed on axis/category, not on `verb`/`sentence`) is not
# touched, so a fallback sentence can still be paired with a label that doesn't fit it ("glad" + "I don't
# know what to do with the purse"). Full option A is the real fix for that; this module only prevents the
# sentence itself from being self-contradictory nonsense.
#
# LOSS_SAFETY_NET_ENABLED = False restores the old (pre-v0.2) behavior exactly.

LOSS_SAFETY_NET_ENABLED = True

# The two mode families observed producing nonsense wording against a feeling/loss target.
_LITERAL_MODES = {"attack", "accept"}

# This module's own reviewed "loss words" list (the negation-and-exclusion decisions
# already made -- e.g. leaving out "alone", "lost", "cry", "gone" as too ambiguous -- already apply here). Not
# just feeling-nouns: "orphan"/"widow" are people, but "attack"/"accept" applied to them in a crying/loss
# scene is the same category error as applying it to "grief" directly (both were flagged examples).
FEELING_WORDS = {
    "grief", "grieve", "grieving", "mourn", "mourning", "mourner", "bereaved", "heartbroken",
    "weep", "wept", "sob", "abandoned", "forsaken", "orphan", "widow", "widowed",
    "loneliness", "hopeless", "despair", "despairing", "despondent", "inconsolable",
    "desolate", "funeral", "coffin",
}

# A small, hand-picked set of loss/destruction/theft verbs (same spirit as db/db_danger.py's hand lists):
# detected in the raw text directly, not via concept tags, so untagged words still count (the draft's own
# reasoning for reading raw text instead of tags, section 5). Deliberately narrow -- see the module docstring.
_LOSS_VERB_WORDS = {
    "destroy", "destroys", "destroyed", "destroying",
    "steal", "steals", "stole", "stolen", "stealing",
    "rob", "robs", "robbed", "robbing",
    "burn", "burns", "burned", "burnt", "burning",
}

_NEGATORS = {"not", "never", "no", "nobody", "none", "n't"}

_FALLBACK_SENTENCES = [
    "I don't know what to do with {np}.",
    "There's nothing I can do about {np}.",
    "I don't have words for {np} right now.",
    "{Np}. I don't know how to react to that.",
]
_FALLBACK_ACTIONS = ["staying quiet", "not knowing what to do", "sitting with it", "going still"]


def _negated_nearby(tokens, idx, window=2):
    lo = max(0, idx - window)
    for t in tokens[lo:idx]:
        low = t.strip(".,!?\"'").lower()
        if low in _NEGATORS or low.endswith("n't"):
            return True
    return False


def _bare(subject):
    """Strips a leading article: response["subject"]/action subject sometimes already comes as "the
    grief" rather than bare "grief" (topic_target/construction_matcher add it upstream)."""
    s = (subject or "").strip()
    low = s.lower()
    for art in ("the ", "a ", "an "):
        if low.startswith(art):
            return s[len(art):]
    return s


def is_loss_scene(raw_text, subject):
    """True when this turn is the narrow case this module exists for: the target is a feeling word, or
    the raw text has an un-negated loss/destruction/theft verb. `subject` is response["subject"] from
    core/response_matrix.py -- may be None, and may already include a leading article."""
    if not LOSS_SAFETY_NET_ENABLED:
        return False
    if _bare(subject).lower() in FEELING_WORDS:
        return True
    if not raw_text:
        return False
    tokens = raw_text.replace("<<", " ").replace(">>", " ").split()
    for i, tok in enumerate(tokens):
        w = tok.strip(".,!?\"'").lower()
        if w in _LOSS_VERB_WORDS and not _negated_nearby(tokens, i):
            return True
    return False


def applies(mode, raw_text, subject):
    """True when both the mode and the scene call for the fallback wording."""
    return LOSS_SAFETY_NET_ENABLED and mode in _LITERAL_MODES and is_loss_scene(raw_text, subject)


def _noun_phrase(subject):
    subj = (subject or "that").strip()
    low = subj.lower()
    if subj[:1].isupper() or low in ("you", "that", "it", "this"):
        return subj
    if low.startswith(("the ", "a ", "an ")):    # already has an article -- don't double it up
        return subj
    return f"the {subj}"


def fallback_sentence(subject, rng=None):
    import random
    rng = rng or random
    np_ = _noun_phrase(subject)
    Np_ = np_[:1].upper() + np_[1:] if np_ else np_
    return rng.choice(_FALLBACK_SENTENCES).format(np=np_, Np=Np_)


def fallback_action(rng=None):
    import random
    rng = rng or random
    return rng.choice(_FALLBACK_ACTIONS)
