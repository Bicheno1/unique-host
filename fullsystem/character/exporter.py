# character/exporter.py — UNIQUE HOST
#
# Exports/imports a LIVE session snapshot: memory (short/medium/long/
# nuclear), engine current state, chemicals, mental states, vitality
# and mind stats. This is separate from character.json (the creation
# seed) — a session_snapshot.json lets the user resume a conversation
# exactly where it left off, without re-answering the questionnaire.


def export_session(ccm) -> dict:
    """Serializes the full live state of a CycleManagerV5 instance."""
    return {
        "schema_version": "unique_host_session_v1_placeholder",
        "somatic_state": ccm.somatic.current_state(),
        "mental_state":  ccm.mental.current_state(),
        "memory_s": {
            "short_term":  ccm.memory_s.short_term,
            "medium_term": ccm.memory_s.medium_term,
            "long_term":   ccm.memory_s.long_term,
        },
        "memory_m": {
            "short_term":  ccm.memory_m.short_term,
            "medium_term": ccm.memory_m.medium_term,
            "long_term":   ccm.memory_m.long_term,
        },
        "chemicals":      dict(ccm.chemicals.levels),
        "mental_states":  dict(ccm.mental_states.levels),
        "vitality_needs": ccm.vitality.all_needs(),
    }


def load_session(ccm, snapshot: dict):
    """Restores a previously exported session onto a live CycleManagerV5."""
    if not snapshot:
        return ccm

    if "somatic_state" in snapshot:
        ccm.somatic.current = dict(snapshot["somatic_state"])
    if "mental_state" in snapshot:
        ccm.mental.current = dict(snapshot["mental_state"])

    mem_s = snapshot.get("memory_s", {})
    ccm.memory_s.short_term  = mem_s.get("short_term", [])
    ccm.memory_s.medium_term = mem_s.get("medium_term", [])
    ccm.memory_s.long_term   = mem_s.get("long_term", [])

    mem_m = snapshot.get("memory_m", {})
    ccm.memory_m.short_term  = mem_m.get("short_term", [])
    ccm.memory_m.medium_term = mem_m.get("medium_term", [])
    ccm.memory_m.long_term   = mem_m.get("long_term", [])

    if "chemicals" in snapshot:
        ccm.chemicals.levels.update(snapshot["chemicals"])
    if "mental_states" in snapshot:
        ccm.mental_states.levels.update(snapshot["mental_states"])

    # TODO: vitality_needs restoration —
    # VitalityStats currently exposes values through nested
    # objects (self._vs.somatic[name]["value"]) rather than flat
    # setters. Wire this up once that internal structure is finalized.
    # (mind_stats no longer exists -- it was a duplicate of vital_system.py,
    # deleted)

    return ccm
