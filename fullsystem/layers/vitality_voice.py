# layers/vitality_voice.py — UNIQUE HOST
#
# VITALITY VOICE — turns a vitality/mind stat in trouble into an EXTRA
# sentence appended after the main verbal output, phrased according to
# whichever of the 16 response-matrix modes (core/response_matrix.py)
# is currently active.
#
# WHY THIS EXISTS ( from conversation): "the engines' internal
# stats... should ask for 'i'm hungry', 'i'm thirsty', 'i'm
# lonely'... but only according to the output mode, as an extra
# message". motors/vitality_stats.py and motors/mind_stats.py already
# track the numbers and produce internal PUSH pressure on the engines
# — this layer is the missing piece that turns "hunger is low" into
# something the host actually SAYS, and lets the same underlying need
# read completely differently depending on the mode the host is
# already in (a starving host under "attack" pushes through it; the
# same hunger under "surrender" reads as fainting).
#
# STATUS: placeholder wording instruction ("for now
# let's put placeholder modes") — one line per (mode × severity tier),
# generic across whichever need triggers it via {need} substitution.
# Not tuned prose, just a first pass covering the shape of the system.
#
# GATING (: "if it has high Gv it may keep it to itself and
# not say that"): a composed/regulated host (high somatic Gv or its
# mental mirror Rr — see CCM_paper_v1.pdf, Gv/Rr are the same
# "held together, adapts to the listener" axis in both engines) holds
# CONCERNING needs back rather than voicing them. CRITICAL needs always
# break through regardless of composure — the body doesn't stay quiet
# forever, no matter how regulated the mind is.

# Somatic base Gv / mental base Rr — see db/db_somatic.py, db/db_mental.py.
# TODO: these are read as constants here instead of pulled
# from the live base_state dict, so a character with a very different
# Fortitude profile would want this threshold recalibrated against
# THEIR OWN base, not the global default. Placeholder, not final.
_GV_BASE  = 25.0
_RR_BASE  = 25.0
_COMPOSED_MARGIN = 15.0   # how far above base counts as "held together"

# value <= this -> "concerning" (matches the existing _label() ranges'
# "hungry"/"thirsty"/"alone" tier in motors/vitality_stats.py and
# motors/mind_stats.py)
_CONCERNING_MAX = 4.0
# value <= this -> "critical" (matches "at limit"/"isolated"/"collapsed")
_CRITICAL_MAX   = 1.5

# Natural-language phrase per need, used to fill {need} in the
# templates below. Extend as more vitality_stats/mind_stats needs get
# wired in here.
_NEED_PHRASE = {
    "hunger":      "hungry",
    "thirst":      "thirsty",
    "energy":      "exhausted",
    "temperature": "overheating",
    "commodity":   "uncomfortable",
    "health":      "unwell",
    "company":     "lonely",
    "purpose":     "adrift",
    "security":    "unsafe",
    "structure":   "scattered",
    "sanity":      "unmoored",
}

# ── the 16 modes × 2 severity tiers ─────────────────────────────────────
# None = the mode stays silent about it at that tier (suppress/desist/
# ignore genuinely don't voice it; that's the point of those modes).
_MODE_MESSAGES = {
    # danger
    "attack":      {"concerning": "No time to think about being {need} right now.",
                     "critical":   "Even like this, I'm not stopping."},
    "surrender":   {"concerning": "I can barely focus past being {need}.",
                     "critical":   "The room tilts. Being {need} finally wins."},   # the "faints"
    "protect":     {"concerning": "I need to take care of this — I'm {need}.",
                     "critical":   "I have to stop. I can't keep going, I'm {need}."},
    "flee":        {"concerning": "I need to do something about this — I'm {need}, now.",
                     "critical":   "I need help. This is bad, I'm {need}."},
    # benefit
    "accept":      {"concerning": "I'll do something about it now, I'm {need}.",
                     "critical":   "I really need this taken care of."},
    "deny":        {"concerning": "I'm fine. It can wait.",
                     "critical":   "I said I'm FINE."},
    "cooperate":   {"concerning": "If it's alright, I could use a moment — I'm {need}.",
                     "critical":   "I don't want to be a burden, but I really need help."},
    "ignore":      {"concerning": None, "critical": None},
    # neutral
    "observe":     {"concerning": "I'm {need}.",                                    # the "I'm hungry"
                     "critical":   "This has gotten serious. I'm {need}."},
    "group":       {"concerning": "Has anyone else felt this too? I'm {need}.",
                     "critical":   "I need to say this — I'm really {need} right now."},
    "formulate":   {"concerning": "I should probably deal with being {need} soon.",
                     "critical":   "This needs to be addressed immediately."},
    # unclassifiable
    "investigate": {"concerning": "Why is this hitting me like this?",
                     "critical":   "Something is wrong. I shouldn't be this {need}."},
    "desist":      {"concerning": None, "critical": None},
    "signal":      {"concerning": "Just so you know — I'm {need}.",
                     "critical":   "I need to be honest: I'm really {need}."},
    "suppress":    {"concerning": None, "critical": None},
}
# NOTE: benefit/ignore and neutral/ignore are the same verb string
# ("ignore") for two different matrix cells (see RESPONSE_MATRIX) —
# both read the same way here, which fits: whatever put the host in an
# "ignore" mode, ignoring the need too is consistent.


def _severity(value: float) -> str | None:
    if value <= _CRITICAL_MAX:
        return "critical"
    if value <= _CONCERNING_MAX:
        return "concerning"
    return None


def _most_urgent_need(needs_status: dict) -> tuple:
    """needs_status: {name: {"value": float, "label": str}, ...} (the
    shape motors/vitality_stats.py::status() and motors/mind_stats.py
    ::status() already produce). Returns (need_name, severity) for the
    LOWEST value currently at concerning/critical, or (None, None)."""
    worst = (None, None, 999.0)
    for name, s in needs_status.items():
        sev = _severity(s.get("value", 10.0))
        if sev and s["value"] < worst[2]:
            worst = (name, sev, s["value"])
    return worst[0], worst[1]


def get_vitality_message(mode: str, needs_status: dict,
                          gv_current: float = None, rr_current: float = None) -> str | None:
    """
    Returns an extra sentence to append after the main verbal output,
    or None if nothing rises to the surface this cycle.

    mode         : response["verb"] from core/response_matrix.py
                   ::select_axis_response() — e.g. "attack", "suppress".
    needs_status : merged vitality_stats.status() + mind_stats.status().
    gv_current/rr_current : current somatic Gv / mental Rr — the
                   "composed, adapts to the listener" axis in each
                   engine (CCM_paper_v1.pdf §1.4). A composed host
                   holds CONCERNING needs back; CRITICAL always breaks
                   through regardless.
    """
    need, severity = _most_urgent_need(needs_status)
    if not need:
        return None

    composed = (
        (gv_current is not None and gv_current >= _GV_BASE + _COMPOSED_MARGIN) or
        (rr_current is not None and rr_current >= _RR_BASE + _COMPOSED_MARGIN)
    )
    if composed and severity == "concerning":
        return None

    template = _MODE_MESSAGES.get(mode, {}).get(severity)
    if not template:
        return None

    return template.format(need=_NEED_PHRASE.get(need, need))
