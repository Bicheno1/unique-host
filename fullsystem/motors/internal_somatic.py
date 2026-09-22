# motors/internal_somatic.py — CCM v8
#
# SOMATIC INTERNAL ENGINE
#
# Three-stage process per cycle:
#
#   Stage 1 — Quadrant → stat pressure
#     The external quadrant determines which stats are being pushed
#     and in which direction this cycle.
#
#   Stage 2 — Quadrant + stat levels → chemical release
#     The combination of active quadrant and current measured stat values
#     determines which chemicals are released and how much.
#     Same quadrant + different stat levels = different chemical response.
#
#   Stage 3 — Chemical levels → internal vector
#     Active chemicals generate the internal somatic vector via
#     chemical_system.get_somatic_push().
#
# Heart rate is a stat that functions as a real-time arousal indicator:
#   - not a depletable resource (has a baseline it returns to)
#   - rises in inviable quadrants and with chemical activation
#   - falls during viable quadrants and recovery
#   - its current level directly gates Stage 2 chemical release

import math
from db.db_somatic     import SOMATIC_KEYS, SOMATIC_BASE
from systems.core_system import update_stat, STAT_DATABASE
from systems.chemical_system import legacy_level as _chem_legacy_level

# ── THREAT-DECLINE TRACKING ──────────────────────────────────
# FIX: the "HR override" rule in _compute_chemical_release used to fire
# whenever heart_rate > 100, *regardless of what happened this cycle* --
# :
# heart rate kept climbing (104->136 bpm) and V kept climbing with it
# (65->260) with zero threatening input, because the override kept
# re-releasing "adrenaline" every cycle it stayed elevated, which kept
# heart_rate elevated, which re-triggered the override -- a closed loop
# with no way to reference what the CURRENT cycle's input actually said.
#
#  : "it needs a threat detector -- if it
# is still active, or if it has already passed (the next input is lower
# intensity) it should go down". _prev_dist stores last cycle's somatic
# distance so this cycle can tell whether the threat is still building
# (dist holding or rising -> override still allowed to fire) or has
# passed (dist dropped meaningfully -> override skipped, let decay work).
# Module-level like STAT_DATABASE itself -- same single-session-process
# assumption already baked into this file (see heart_rate there).
_threat_state = {"prev_dist": 0.0}


def _is_threat_still_active(dist: float, prev_dist: float) -> bool:
    """True if this cycle's somatic distance held steady or grew versus
    last cycle (threat still building/ongoing) -- False if it dropped
    meaningfully (threat passed, character is coming down on its own,
    the HR override should NOT re-fuel it)."""
    if prev_dist <= 0:
        return dist > 0
    return dist >= prev_dist * 0.9

# ── HEART RATE LABELS ────────────────────────────────────────────────────────

def _hr_label(bpm: float) -> str:
    if bpm < 60:  return "bradycardia"
    if bpm < 80:  return "resting"
    if bpm < 100: return "elevated"
    if bpm < 130: return "high"
    if bpm < 160: return "very_high"
    return "maximum"


# ── STAGE 1: QUADRANT → STAT PRESSURE ────────────────────────────────────────
#
# Each quadrant defines:
#   hr_delta     : heart rate change this cycle (bpm)
#   energy_drain : how much energy this quadrant consumes

_QUADRANT_STAT_PRESSURE = {
    "inviable-localized": {
        "hr_delta":     +12.0,   # acute threat — HR spikes fast
        "energy_drain":  0.08,
    },
    "inviable-globalized": {
        "hr_delta":     +5.0,    # chronic stress — HR rises slowly
        "energy_drain":  0.12,   # but drains more energy
    },
    "viable-localized": {
        "hr_delta":     +3.0,    # alert/ready — mild elevation
        "energy_drain":  0.03,
    },
    "viable-globalized": {
        "hr_delta":     -4.0,    # recovery — HR falls
        "energy_drain":  0.01,
    },
}


def _update_heart_rate(quadrant: str, chemical_levels: dict) -> float:
    """
    Updates heart_rate in core_system based on quadrant pressure
    and active chemical levels. Returns current bpm after update.
    """
    current_hr = STAT_DATABASE.get("heart_rate", {}).get("value", 70.0)
    baseline   = STAT_DATABASE.get("heart_rate", {}).get("baseline", 70.0)

    pressure = _QUADRANT_STAT_PRESSURE.get(quadrant, {"hr_delta": 0.0})
    delta    = pressure["hr_delta"]

    # Chemicals amplify HR change
    # NOTE: chemical_levels is now keyed by mode name (attack, protect, ...)
    # rather than named chemical — legacy_level() sums the mode(s) that
    # inherited each old chemical's physiological role (see
    # systems/chemical_system.py LEGACY_TRIGGER_TO_MODES).
    # "adrenaline" and "noradrenaline" both map to the same modes
    # (attack + flee — see LEGACY_TRIGGER_TO_MODES) under the new design,
    # so they are no longer independent signals. Read once and split the
    # old two-term weight (4.0 + 3.0) into a single 7.0 term below instead
    # of double-counting the same level twice.
    adrena  = _chem_legacy_level(chemical_levels, "adrenaline")
    cortis  = _chem_legacy_level(chemical_levels, "cortisol")
    oxytoc  = _chem_legacy_level(chemical_levels, "oxytocin")
    serot   = _chem_legacy_level(chemical_levels, "serotonin")

    # Activating chemicals push HR up
    delta += adrena  * 7.0   # combined former adrenaline(4.0) + noradrenaline(3.0) weight
    delta += cortis  * 1.5

    # Calming chemicals pull HR toward baseline
    delta -= oxytoc * 2.0
    delta -= serot  * 1.5

    # Decay toward baseline (passive recovery)
    decay_pull = (baseline - current_hr) * 0.05
    delta += decay_pull

    new_hr = max(40.0, min(180.0, current_hr + delta))
    update_stat("heart_rate", new_hr, label=_hr_label(new_hr))
    return new_hr


# ── STAGE 2: QUADRANT + STATS → CHEMICAL RELEASE ────────────────────────────
#
# Each rule: trigger conditions → release chemical at given amount.
# Amount scales with how deep into the condition the system is.

def _compute_chemical_release(
    quadrant: str,
    heart_rate: float,
    energy: float,
    current_chemicals: dict,
    threat_still_active: bool = True,
) -> dict:
    """
    Returns {chemical_name: amount} to release this cycle.
    """
    releases = {}

    # ── INVIABLE-LOCALIZED — acute threat ────────────────────────────────────
    if quadrant == "inviable-localized":

        # HR > 85: adrenaline kicks in
        if heart_rate > 85:
            depth = min((heart_rate - 85) / 45, 1.0)   # 0→1 over 85–130 bpm
            releases["adrenaline"] = 0.5 + depth * 1.5

        # HR > 100: noradrenaline added (vigilance + threat scanning)
        if heart_rate > 100:
            depth = min((heart_rate - 100) / 60, 1.0)
            releases["noradrenaline"] = 0.3 + depth * 1.0

        # Low energy under threat → cortisol spike (mobilize reserves)
        if energy < 4.0:
            depth = 1.0 - (energy / 4.0)
            releases["cortisol"] = 0.4 + depth * 0.8

        # Already high adrenaline + HR very high → noradrenaline surge
        # (both legacy names now land on attack/flee — see note in
        # _update_heart_rate above)
        if _chem_legacy_level(current_chemicals, "adrenaline") > 3.0 and heart_rate > 115:
            releases["noradrenaline"] = releases.get("noradrenaline", 0) + 0.5

    # ── INVIABLE-GLOBALIZED — chronic stress ─────────────────────────────────
    elif quadrant == "inviable-globalized":

        # Sustained cortisol (chronic load)
        releases["cortisol"] = 0.4

        # Low energy under chronic stress → more cortisol
        if energy < 3.0:
            depth = 1.0 - (energy / 3.0)
            releases["cortisol"] += depth * 0.6

        # HR moderately elevated → mild noradrenaline
        if heart_rate > 90:
            releases["noradrenaline"] = 0.2

    # ── VIABLE-LOCALIZED — alert/ready ───────────────────────────────────────
    elif quadrant == "viable-localized":

        # Mild dopamine (goal-oriented, active)
        if heart_rate < 90:
            releases["dopamine"] = 0.2

        # If previously under threat and now viable: endorphin release
        if _chem_legacy_level(current_chemicals, "adrenaline") > 1.0:
            releases["endorphins"] = 0.3

    # ── VIABLE-GLOBALIZED — recovery/safe ────────────────────────────────────
    elif quadrant == "viable-globalized":

        # Serotonin (calm, safe, recovery)
        releases["serotonin"] = 0.3

        # Oxytocin if HR is already low (genuine safety, not just low arousal)
        if heart_rate < 80:
            releases["oxytocin"] = 0.2

        # Post-threat recovery bonus: endorphins if cortisol was high
        if _chem_legacy_level(current_chemicals, "cortisol") > 2.0:
            releases["endorphins"] = 0.2

    # ── HR override — high heart rate triggers adrenaline regardless of quadrant
    # This represents the body responding to its own arousal signal.
    # Fix: only while the threat is still active/building THIS
    # cycle -- otherwise this alone is what created the runaway loop (see
    # module docstring). Once dist drops from last cycle, this stops
    # re-fueling and heart rate is left to fall on its own decay_pull.
    if heart_rate > 100 and quadrant not in ("inviable-localized",) and threat_still_active:
        depth = min((heart_rate - 100) / 60, 1.0)
        releases["adrenaline"] = releases.get("adrenaline", 0) + 0.3 + depth * 0.5

    return releases


# ── STAGE 3: CHEMICAL PUSH → INTERNAL VECTOR ────────────────────────────────
# Handled by chemical_system.get_somatic_push() — already implemented.
# This function just orchestrates the three stages.


# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def process(D: tuple, vitality_stats: dict, chemical_system=None) -> dict:
    """
    D              : (cx, cy) — center of mass of the somatic rhomboid (D1)
    vitality_stats : all_needs() dict
    chemical_system: ChemicalSystem instance

    Returns internal somatic vector {V, I, Lv, Gv} + metadata.
    """
    cx, cy = D
    dist   = math.sqrt(cx**2 + cy**2)

    threat_still_active = _is_threat_still_active(dist, _threat_state["prev_dist"])
    _threat_state["prev_dist"] = dist

    # Resolve quadrant from D1
    if   cy >= 0 and cx >= 0: quadrant = "viable-localized"
    elif cy >= 0 and cx <  0: quadrant = "viable-globalized"
    elif cy <  0 and cx >= 0: quadrant = "inviable-localized"
    else:                      quadrant = "inviable-globalized"

    # Current stat values
    energy_stat = vitality_stats.get("energy", {})
    energy      = energy_stat.get("value", 8.0) if isinstance(energy_stat, dict) else 8.0

    current_chemicals = chemical_system.levels if chemical_system else {}

    # ── STAGE 1: update heart rate ────────────────────────────────────────────
    heart_rate = _update_heart_rate(quadrant, current_chemicals)

    # ── STAGE 2: release chemicals ────────────────────────────────────────────
    releases = _compute_chemical_release(quadrant, heart_rate, energy, current_chemicals, threat_still_active)

    if chemical_system:
        for chem_name, amount in releases.items():
            chemical_system.release(chem_name, amount)

    # ── STAGE 3: get internal vector from chemicals ───────────────────────────
    if chemical_system:
        result = chemical_system.get_somatic_push()
    else:
        result = {k: 0.0 for k in SOMATIC_KEYS}

    result["_pipeline"]   = "internal_somatic_v8"
    result["_quadrant"]   = quadrant
    result["_heart_rate"] = round(heart_rate, 1)
    result["_releases"]   = releases
    return result
