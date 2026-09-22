# systems/plasticity_system.py — CCM v5
#
# Plasticity — two-step learning:
#
# STEP 1 — Modify TAG_VALUES (existing)
#   At the end of each cycle, for each active tag in the scene:
#   - Determines how much it changes based on memory history
#   - Determines direction: state rose → sensitization, fell → habituation
#   - Modifies all axes of the tag proportionally
#
#   Deltas by history:
#     first exposure  → DELTA_FIRST   (minimum)
#     medium_term     → DELTA_MEDIUM
#     long_term       → DELTA_LONG
#     nuclear         → DELTA_NUCLEAR (maximum)
#
# step 2 — Check links in db_concepts (new)
#   Only activates if STEP 1 modified any tag.
#   For each active concept, compares its highest activation value
#   with the highest value of each of its related.
#   If the difference is > RELATED_THRESHOLD (20) → breaks the link in related.
#
#   Example:
#     ghost has I=125 (highest value)
#     danger has I=110 (highest value)
#     |125 - 110| = 15 < 20 → they remain related
#
#     After habituation ghost drops to I=80
#     |80 - 110| = 30 > 20 → danger leaves ghost's related
#
# OPENING (dist_mental < 30):
#   In opening range the plasticity learns at maximum — DELTA_NUCLEAR
#   independently of memory history.

from db.db_somatic  import TAG_VALUES_SOMATIC, SOMATIC_KEYS, SOMATIC_MAX
from db.db_mental   import TAG_VALUES_MENTAL,  MENTAL_KEYS,  MENTAL_MAX
from db.db_concepts import CONCEPTS

# OPENING SYSTEM precondition ( paper): "activates when the coherence center approaches
# zero FOLLOWING a high-absence or high-inviability event". The code opened whenever dist_mental < 30,
# with no event needed, and real characters rest at 3-21, so every active word learned at the maximum
# step (0.25) every turn and calm words drifted towards "danger" (birds sing: I 175 -> 199 in 12 turns).
# Now the maximum step also needs a threat event (memory_system THREAT events) in progress or closed
# within OPENING_WINDOW_CYCLES. Outside the window the usual tier deltas apply.
# OPENING_REQUIRES_THREAT = False restores the old behaviour.
OPENING_REQUIRES_THREAT = True
OPENING_WINDOW_CYCLES   = 15

DELTA_FIRST   = 0.02
DELTA_MEDIUM  = 0.06
DELTA_LONG    = 0.12
DELTA_NUCLEAR = 0.25

MIN_VAL        = 0.01
MIN_CHANGE_MAG = 0.15

# step 2 — divergence threshold to break a link in related
RELATED_THRESHOLD = 20.0


# ── step 1 HELPERS ────────────────────────────────────────────────────────────

def _get_delta(concept_name, active_concepts, memory, dist_mental=None, opening_allowed=True):
    # Full opening → maximum learning (only after a high-inviability/absence event, see above)
    if dist_mental is not None and dist_mental < 30.0 and (opening_allowed or not OPENING_REQUIRES_THREAT):
        return DELTA_NUCLEAR

    in_long    = False
    is_nuclear = False
    for event in memory.long_term:
        overlap = set(event["concepts"]) & set(active_concepts)
        if overlap:
            in_long = True
            if event["is_nuclear"]:
                is_nuclear = True
                break

    if is_nuclear:   return DELTA_NUCLEAR
    if in_long:      return DELTA_LONG

    in_medium = any(
        set(e["concepts"]) & set(active_concepts)
        for e in memory.medium_term
    )
    if in_medium:    return DELTA_MEDIUM
    return DELTA_FIRST


def _direction(state_before, state_after, keys):
    mag_before = sum(state_before.get(k, 0) ** 2 for k in keys) ** 0.5
    mag_after  = sum(state_after.get(k, 0)  ** 2 for k in keys) ** 0.5
    diff = mag_after - mag_before
    if abs(diff) < MIN_CHANGE_MAG:
        return 0
    return 1 if diff > 0 else -1


# Fix: _direction above is a single scalar
# (did the state get more or less intense overall) applied to EVERY axis
# of the tag uniformly by _modify_tag. But V/I and P/A aren't a
# generic magnitude -- valence.py builds them as an exact complementary
# pair at creation time (V=value, I=10-value, same for P/A -- see
# valence.py line ~147, "complement = 10.0 - value"). Adding the SAME
# delta to both V and I leaves V-I completely unchanged (proven: tested
# 6 cycles of a bad experience on a liked concept, P-A stayed at exactly
# 20 before and after) -- mathematically, a shared additive delta on a
# subtraction is a no-op on the subtraction. So the old uniform
# _direction could inflate a concept's reaction but could never make
# something liked start being disliked.
# _valence_direction instead reads which way *this specific cycle's
# change* moved the V/I (or P/A) balance -- net = (change in V) - (change
# in I). A "negative"/bad cycle pushes I up and/or V down more than the
# reverse -- net < 0. That sign then pushes V and I (or P and A) in
# OPPOSITE directions in _modify_valence_pair below, which is the only
# way the balance can actually shift over repeated exposure. Lv/Gv/Er/Rr
# are NOT part of this -- per valence.py's own docstring they encode a
# different personality axis (empathy vs ego), not liked/disliked, so
# they keep using the old uniform _direction (intensity only).
def _valence_direction(state_before, state_after, pos_key, neg_key):
    d_pos = state_after.get(pos_key, 0) - state_before.get(pos_key, 0)
    d_neg = state_after.get(neg_key, 0) - state_before.get(neg_key, 0)
    net = d_pos - d_neg
    if abs(net) < MIN_CHANGE_MAG:
        return 0
    return 1 if net > 0 else -1


# CORRECTION (same day, after reading the full CCM paper, "Pure
# Magnitudes and Semantic Orientation"): the fix above was half right.
# V/I and P/A DO need a signed, per-axis update instead of the old
# uniform one -- that part stands. But the specific mechanism (push V
# and I in OPPOSITE directions, i.e. "steal" from one to feed the
# other) isn't what the paper describes., verbatim: "Stored values
# are pure magnitudes... This preserves the additive nature of negative
# factors -- inviability accumulates as inviability." Orientation
# (V:+1, I:-1) is applied only at EVALUATION time (V - I); the two
# stored magnitudes accumulate INDEPENDENTLY. A bad experience doesn't
# need to lower V to read as worse -- it just needs to raise I, and I's
# fixed -1 orientation is what makes the combined V-I reading move
# negative. Forcing V down at the same time double-counts the shift and
# invents a zero-sum trade-off the model doesn't ask for. Corrected:
# only the ONE key matching this cycle's sign gets the delta; the other
# is left untouched, exactly like DELTA_FIRST/MEDIUM/LONG/NUCLEAR
# already only ever ADD, never subtract, elsewhere in this file.
def _modify_valence_pair(tag_name, tag_db, delta, sign, pos_key, neg_key, max_val):
    if tag_name not in tag_db or sign == 0:
        return
    target = pos_key if sign > 0 else neg_key
    tag_db[tag_name][target] = max(MIN_VAL, min(max_val, tag_db[tag_name].get(target, 0) + delta))


def _modify_tag(tag_name, tag_db, delta, direction, max_val, valence_sign=None):
    """
    `direction` (old, magnitude-only): applied to every key EXCEPT the
    valence pair, when a sign is available for it (see fix above).
    `valence_sign`: (sign, pos_key, neg_key) or None. When given, pos_key
    and neg_key are skipped from the uniform pass below and moved in
    opposite directions instead via _modify_valence_pair().
    """
    if tag_name not in tag_db:
        return
    skip = set()
    if valence_sign is not None:
        sign, pos_key, neg_key = valence_sign
        if pos_key in tag_db[tag_name] and neg_key in tag_db[tag_name]:
            _modify_valence_pair(tag_name, tag_db, delta, sign, pos_key, neg_key, max_val)
            skip = {pos_key, neg_key}
    for k in list(tag_db[tag_name].keys()):
        if k in skip:
            continue
        old = tag_db[tag_name][k]
        tag_db[tag_name][k] = max(MIN_VAL, min(max_val, old + delta * direction))


def _concept_max_value(concept_name, tag_db, keys):
    """
    Calculates the highest activation value of a concept
    by summing its tag vectors and taking the maximum component.
    """
    c = CONCEPTS.get(concept_name, {})
    # Collect all tags of the concept from its related
    tags = set()
    for branches in c.get("related", {}).values():
        for motor in ("somatic", "mental"):
            tags.update(branches.get(motor, []))

    if not tags:
        return 0.0

    total = {k: 0.0 for k in keys}
    count = 0
    for tag in tags:
        if tag in tag_db:
            for k in keys:
                total[k] += tag_db[tag].get(k, 0.0)
            count += 1

    if count == 0:
        return 0.0

    avg = {k: total[k] / count for k in keys}
    return max(avg.values())


# ── step 2 — CHECK LINKS IN db_concepts ───────────────────────────────────

def _check_related_links(active_concepts, tag_db, keys):
    """
    For each active concept, compares its highest activation value
    with each related. If the difference > RELATED_THRESHOLD → breaks the link.

    Returns dict: {concept: [related_removidos]}
    """
    removed = {}

    for concept_name in active_concepts:
        c = CONCEPTS.get(concept_name)
        if not c:
            continue

        concept_max = _concept_max_value(concept_name, tag_db, keys)
        to_remove   = []

        for related_name in list(c.get("related", {}).keys()):
            # BUG FIX (-09-0X): this loop's whole premise is "related_name is
            # the NAME OF ANOTHER CONCEPT, compare divergence against
            # it" -- true for the old hand-authored graph (ghost.related
            # has "danger"/"fear"/... as keys, all real CONCEPTS
            # entries). It is NOT true for the newer valence mechanism
            # (character/valence.py): its "related" keys are relation-
            # TYPE labels ("valence", "group__<name>", tree's
            # "shared__<branch>"), not concept names. CONCEPTS.get(key)
            # returned None for those, _concept_max_value then
            # returned 0.0, and abs(real_value - 0.0) is always >
            # RELATED_THRESHOLD -- so EVERY valence-migrated concept
            # (family/animal/core_fear/core_comfort/the 787 tree words/
            # the 25 words migrated) had its one and only
            # `related` entry deleted the very first time plasticity
            # touched it, going permanently silent in pre_input's
            # _concept_value from then on (confirmed: reproduced with
            # "family", untouched by today's migration, so this predates
            # it). Skip labels that aren't themselves a real concept --
            # there is nothing to check divergence against, so no
            # decision to make here, not a design choice being changed.
            if related_name not in CONCEPTS:
                continue

            # PYRAMID FIX ( from conversation): related
            # branches aren't one flat hierarchy -- they belong to
            # different "pyramids" (the rhomboid's 4 axes, per the CCM
            # paper's geometry), and losing a rung in one doesn't have
            # to lose it in another. Concretely: "ghost"~"fear" is a
            # genuine EMOTIONAL association (the paper's own dissociation
            # example, -- can legitimately fade as experience
            # diverges) but "bird"~"fly" is a FACTUAL capability, not a
            # feeling -- it shouldn't dissolve just because the
            # character's emotional reading of "bird" moved. The
            # existing signal for telling them apart is already on every
            # concept: capabilities are type="action" (fly/walk/run/
            # hide/breathe); associations are everything else the old
            # hand-authored graph used (status concepts like fear/danger/
            # threat/calm/trust). Protect the factual pyramid; only let
            # the emotional/associative one dissociate, which is what
            # this mechanism was actually meant to model.
            if CONCEPTS[related_name].get("type") == "action":
                continue

            related_max = _concept_max_value(related_name, tag_db, keys)
            if abs(concept_max - related_max) > RELATED_THRESHOLD:
                to_remove.append(related_name)

        if to_remove:
            for r in to_remove:
                del c["related"][r]
            removed[concept_name] = to_remove

    return removed


# ── PUBLIC API ───────────────────────────────────────────────────────────────

def apply_plasticity(active_concepts, memory, state_before_s, state_after_s,
                     state_before_m, state_after_m, dist_mental=None, opening_allowed=True):
    """
    Called at the end of each cycle.

    active_concepts : list[str]
    memory          : MemorySystem
    state_before_*  : dict with engine values before the cycle
    state_after_*   : dict with engine values after the cycle
    dist_mental     : current mental distance (to detect opening)
    opening_allowed : a threat event is in progress / recent (see OPENING_REQUIRES_THREAT)
    """
    changed = {
        "somatic":      {},
        "mental":       {},
        "links_removed": {},
    }

    dir_s = _direction(state_before_s, state_after_s, SOMATIC_KEYS)
    dir_m = _direction(state_before_m, state_after_m, MENTAL_KEYS)

    # Signed valence direction (see fix above) -- independent of dir_s/
    # dir_m, which only say "more or less intense", not "better or worse".
    valence_sign_s = _valence_direction(state_before_s, state_after_s, "V", "I")
    valence_sign_m = _valence_direction(state_before_m, state_after_m, "P", "A")

    if dir_s == 0 and dir_m == 0 and valence_sign_s == 0 and valence_sign_m == 0:
        return changed  # nothing significant — does not modify

    # ── step 1 ────────────────────────────────────────────────────────────────
    for concept_name in active_concepts:
        c = CONCEPTS.get(concept_name)
        if not c:
            continue

        delta = _get_delta(concept_name, active_concepts, memory, dist_mental, opening_allowed)

        # Somatic — tags from related[somatic]
        if dir_s != 0 or valence_sign_s != 0:
            tags_s = set()
            for branches in c.get("related", {}).values():
                tags_s.update(branches.get("somatic", []))
            for tag_name in tags_s:
                if tag_name in TAG_VALUES_SOMATIC:
                    _modify_tag(tag_name, TAG_VALUES_SOMATIC, delta, dir_s, SOMATIC_MAX,
                                valence_sign=(valence_sign_s, "V", "I"))
                    changed["somatic"][tag_name] = {
                        "delta":     round(delta * dir_s, 4),
                        "direction": "up" if dir_s > 0 else ("down" if dir_s < 0 else "flat"),
                        "valence":   "toward V (liked)" if valence_sign_s > 0 else ("toward I (disliked)" if valence_sign_s < 0 else "unchanged"),
                        "new_I":     round(TAG_VALUES_SOMATIC[tag_name].get("I", 0), 4),
                        "new_V":     round(TAG_VALUES_SOMATIC[tag_name].get("V", 0), 4),
                    }

        # Mental — tags from related[mental]
        if dir_m != 0 or valence_sign_m != 0:
            tags_m = set()
            for branches in c.get("related", {}).values():
                tags_m.update(branches.get("mental", []))
            for tag_name in tags_m:
                if tag_name in TAG_VALUES_MENTAL:
                    _modify_tag(tag_name, TAG_VALUES_MENTAL, delta, dir_m, MENTAL_MAX,
                                valence_sign=(valence_sign_m, "P", "A"))
                    changed["mental"][tag_name] = {
                        "delta":     round(delta * dir_m, 4),
                        "direction": "up" if dir_m > 0 else ("down" if dir_m < 0 else "flat"),
                        "valence":   "toward P (liked)" if valence_sign_m > 0 else ("toward A (disliked)" if valence_sign_m < 0 else "unchanged"),
                        "new_A":     round(TAG_VALUES_MENTAL[tag_name].get("A", 0), 4),
                        "new_P":     round(TAG_VALUES_MENTAL[tag_name].get("P", 0), 4),
                    }

    # ── STEP 2 — only if step 1 modified anything ──────────────────────────────
    if changed["somatic"] or changed["mental"]:
        # Check somatic links
        removed_s = _check_related_links(active_concepts, TAG_VALUES_SOMATIC, SOMATIC_KEYS)
        # Check mental links
        removed_m = _check_related_links(active_concepts, TAG_VALUES_MENTAL, MENTAL_KEYS)

        all_removed = {}
        for k, v in {**removed_s, **removed_m}.items():
            all_removed.setdefault(k, [])
            for r in v:
                if r not in all_removed[k]:
                    all_removed[k].append(r)

        changed["links_removed"] = all_removed

    return changed
