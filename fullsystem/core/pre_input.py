# core/pre_input.py — CCM v5
#
# Pre-input — categorizer and amplifier
#
# FLOW:
#   step 1 — Identify focus and calculate multiplier
#     - focus = concept of highest priority (illogical > subject > action > status > environment > object)
#     - multiplier = number of related items of the focus that appear in the related
#       of other concepts in the scene + 1
#     - Example: ghost has [danger, fear, defenseless]
#                dark  has [fear, danger, uncertainty]
#                fear matches → +1, danger matches → +1
#                ghost = x3 (2 matches + 1)
#
#   step 2 — Search focus in memory
#     - If the focus appears in short/medium/long term of the memory system
#     - The graph of the event is taken → median point (start, peak, end)
#     - That vector enters via the interference formula on top of step 1 result
#
#   result → goes to the external motors (somatic and mental)

from collections import Counter

PRIORITY = ["illogical", "subject", "action", "status", "environment", "object", "quality"]
STATUS_SUBTYPE_PRIORITY = ["threat", "emotional", "physical", "social", "safety", "condition"]

VISUAL_SENSE   = "sight"
RECEPTOR_SENSES = {"touch", "hearing", "smell", "taste"}


# ── step 1 — focus Y multiplier ─────────────────────────────────────────────

def _get_focus(concept_names, concepts_db):
    best_name, best_score = None, (999, 999)
    for name in concept_names:
        c = concepts_db.get(name)
        if not c:
            continue
        ctype   = c.get("type", "object")
        subtype = c.get("subtype", "")
        type_score = PRIORITY.index(ctype) if ctype in PRIORITY else 999
        sub_score  = STATUS_SUBTYPE_PRIORITY.index(subtype) if (ctype == "status" and subtype in STATUS_SUBTYPE_PRIORITY) else 999
        if (type_score, sub_score) < best_score:
            best_score = (type_score, sub_score)
            best_name  = name
    return best_name


def _get_multiplier(focus_name, concept_names, concepts_db):
    """
    Counts how many related of the focus appear in the related of other concepts.
    Multiplier = matches + 1
    """
    focus = concepts_db.get(focus_name, {})
    focus_related = set(focus.get("related", []))
    if not focus_related:
        return 1

    coincidences = 0
    for name in concept_names:
        if name == focus_name:
            continue
        other = concepts_db.get(name, {})
        other_related = set(other.get("related", []))
        coincidences += len(focus_related & other_related)

    return coincidences + 1


def _concept_value(name, concepts_db, tag_values, keys, motor="somatic"):
    """
    Calculates the vector of a concept by summing the tag_values of all its
    related[motor]. Accumulation is done in oriented space — each
    factor has intrinsic polarity (ORIENTATION) — and the result is
    returned as pure magnitudes (CCM convention).
    """
    from core.formulas import ORIENTATION, oriented, magnitude
    c = concepts_db.get(name)
    if not c:
        return None

    # Collect all tags of the engine from the related
    tag_counts = {}
    for related_node, branches in c.get("related", {}).items():
        for tag in branches.get(motor, []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    tag_vals = []
    for tag, count in tag_counts.items():
        if tag in tag_values:
            weighted = {k: tag_values[tag][k] * count for k in keys if k in tag_values[tag]}
            tag_vals.append(weighted)

    if not tag_vals:
        return None

    # Average in oriented space to preserve semantics
    result = {}
    for k in keys:
        # Sum of the oriented values of each tag
        total_oriented = sum(oriented(k, v.get(k, 0)) for v in tag_vals)
        avg_oriented   = total_oriented / len(tag_vals)
        result[k]      = magnitude(k, avg_oriented)
    return result


# ── step 2 — memory ──────────────────────────────────────────────────────────

def _memory_vector(focus_name, memory, keys, max_val):
    """
    Searches for the focus in short/medium/long term.
    If found, calculates the median point of the graph (start, peak, end)
    and converts it into an interference vector.
    """
    if memory is None:
        return None

    all_memories = (
        list(memory.short_term) +
        list(memory.medium_term) +
        list(memory.long_term)
    )

    matching = [
        e for e in all_memories
        if focus_name in e.get("concepts", [])
    ]

    if not matching:
        return None

    # Take the most relevant — highest peak
    best = max(matching, key=lambda e: e.get("mental_peak", 0) + e.get("somatic_peak", 0))

    graph = best.get("graph", {})
    start = graph.get("start", (0, 0))
    peak  = graph.get("peak",  (0, 0))
    end   = graph.get("end",   (0, 0))

    # Median point of the 3 graph points (pure magnitude, D/C) -- used
    # only to scale HOW STRONGLY the memory pushes.
    pD, pC = peak
    sD, sC = start
    eD, eC = end

    median_D = (sD + pD + eD) / 3.0
    median_C = (sC + pC + eC) / 3.0

    intensity = (median_D + median_C) / 2.0
    scale     = min(intensity / max_val, 1.0)

    # Fix: the real direction -- which way to push --
    # does NOT come from the magnitude above (that was lost when computing
    # the euclidean distance). It comes from the sign stored in the event
    # (memory_system.py: peak_sign_somatic/mental). If the memory was
    # "good" (viable/present), it pushes toward V/P -- e.g. the dog that
    # calms. If it was "bad" (threat/absence), it pushes toward I/A, as
    # before. Without this data (old events saved before the fix) it falls
    # back to the previous behavior (always toward threat) via the default.
    if "V" in keys:
        lv_gv, v_i = graph.get("peak_sign_somatic", (0.0, -1.0))
        vec = {k: 0.0 for k in keys}
        if v_i >= 0:
            # viable/positive memory -- helps, raises V
            vec["V"]  = scale * max_val * 0.3
        else:
            # threat memory -- as before, raises I
            vec["I"]  = scale * max_val * 0.3
        if lv_gv >= 0:
            vec["Lv"] = scale * max_val * 0.2
        else:
            vec["Gv"] = scale * max_val * 0.2
        return vec
    else:
        er_rr, p_a = graph.get("peak_sign_mental", (0.0, -1.0))
        vec = {k: 0.0 for k in keys}
        if p_a >= 0:
            # present/positive memory -- helps, raises P (e.g. the dog
            # that calms when you are in high Absence)
            vec["P"]  = scale * max_val * 0.3
        else:
            # distressing memory -- as before, raises A
            vec["A"]  = scale * max_val * 0.3
        if er_rr >= 0:
            vec["Er"] = scale * max_val * 0.2
        else:
            vec["Rr"] = scale * max_val * 0.2
        return vec


# ── MAIN SEMANTIC PIPELINE ──────────────────────────────────────────────

def _pre_input_semantic(concept_names, concepts_db, tag_values, keys, max_val, memory=None, motor="somatic"):
    from core.formulas import ORIENTATION, oriented, magnitude, apply_input

    focus_name = _get_focus(concept_names, concepts_db)
    if not focus_name:
        return None

    focus_vec = _concept_value(focus_name, concepts_db, tag_values, keys, motor)
    if not focus_vec:
        return None

    # step 1 — multiplier by shared related items
    multiplier = _get_multiplier(focus_name, concept_names, concepts_db)

    # apply multiplier in oriented space → return magnitude
    result = {}
    for k in keys:
        scaled = oriented(k, focus_vec[k]) * multiplier
        result[k] = min(max_val, magnitude(k, scaled))

    # Semi-foci (remaining concepts) enter with weight 0.5 in oriented space
    for name in concept_names:
        if name == focus_name:
            continue
        vec = _concept_value(name, concepts_db, tag_values, keys, motor)
        if not vec:
            continue
        for k in keys:
            current_oriented = oriented(k, result[k])
            extra_oriented   = oriented(k, vec[k]) * 0.5
            combined         = current_oriented + extra_oriented
            result[k]        = min(max_val, magnitude(k, combined))

    # step 2 — memory
    mem_vec = _memory_vector(focus_name, memory, keys, max_val)
    if mem_vec:
        result = apply_input(result, mem_vec, keys)

    result["_focus"]      = focus_name
    result["_multiplier"] = multiplier
    result["_concepts"]   = concept_names
    result["_memory"]     = mem_vec is not None
    result["_pipeline"]   = "semantic"
    return result


# ── receptor PIPELINE ─────────────────────────────────────────────────────────

def _pre_input_receptor(receptor_type, value, zone=None):
    from db.db_receptors import lookup_receptor, lookup_receptor_weighted
    from systems.core_system import update_stat
    match = lookup_receptor_weighted(receptor_type, value, zone) if zone else lookup_receptor(receptor_type, value)
    if not match:
        return None
    update_stat(stat_key=match["stat"], value=value, label=match["label"],
                somatic=match["somatic"], mental=match["mental"])
    result = dict(match["somatic"])
    result.update({"_token": receptor_type, "_type": "receptor", "_label": match["label"],
                   "_stat": match["stat"], "_pipeline": "receptor", "_zone": zone or "unspecified",
                   "_mental": match["mental"]})
    return result


def _pre_input_receptor_mental(receptor_type, value, zone=None):
    from db.db_receptors import lookup_receptor, lookup_receptor_weighted
    from systems.core_system import update_stat
    match = lookup_receptor_weighted(receptor_type, value, zone) if zone else lookup_receptor(receptor_type, value)
    if not match:
        return None
    update_stat(stat_key=match["stat"], value=value, label=match["label"],
                somatic=match["somatic"], mental=match["mental"])
    result = dict(match["mental"])
    result.update({"_token": receptor_type, "_type": "receptor", "_label": match["label"],
                   "_stat": match["stat"], "_pipeline": "receptor", "_zone": zone or "unspecified",
                   "_somatic": match["somatic"]})
    return result


# ── CONTRADICTION DETECTION ───────────────────────────────────────────────

# IMPLICIT CAPABILITIES — the "pyramid" layer ( from
# conversation): "like a food pyramid — the top has the most common
# thing, everything below inherits it, plus its own explicit
# specifics." Keyed by (type, subtype), same fields every concept
# already carries. detect_contradiction used to ONLY check a
# concept's own EXPLICIT related keys — fine for bird's specific "fly"
# (not every animal flies, so that has to stay explicit, per-species),
# but wrong for generic things any person/animal can just do: "hero"
# and "bandit" (subtype="person") have nothing but their emotional
# reaction tags in `related` (calm/trust, fear/threat) -- no capability
# was ever listed for them, so EVERY action came back as a false
# contradiction ("a hero walks" read as false, same as "a hero flies"
# would). This is the implicit tier: generic enough to be safe to
# assume for the whole subtype, checked in ADDITION to (never instead
# of) each concept's own explicit related keys.
IMPLICIT_CAPABILITIES = {
    ("subject", "person"):       ["walk", "run", "hide", "breathe"],
    ("subject", "person_known"): ["walk", "run", "hide", "breathe"],
    ("subject", "animal"):       ["walk", "run", "hide", "breathe"],
    # "social" (angelo/face) and anything else not listed here gets no
    # implicit tier -- falls back to explicit-only, same as before.
}


def _grammatical_subject_verb_pairs(raw_text, concepts_db):
    """
    Real (subject_concept, action_concept) pairs the text actually
    asserts, via spaCy's dependency parse — a subject token whose dep_
    is nsubj/nsubjpass, paired with its OWN head verb, not just any verb
    appearing somewhere else in the sentence/scene.

    Returns None if raw_text is empty or spaCy isn't available (caller
    falls back to the old bag-of-concepts behavior in that case).
    """
    if not raw_text:
        return None
    try:
        from core.construction_matcher import get_nlp
        from db.db_concepts import resolve_concept
    except Exception:
        return None

    try:
        doc = get_nlp()(raw_text)
    except Exception:
        return None

    pairs = []
    for tok in doc:
        if tok.dep_ not in ("nsubj", "nsubjpass"):
            continue
        subj_name = resolve_concept(tok.lemma_)
        act_name  = resolve_concept(tok.head.lemma_)
        if not subj_name or not act_name:
            continue
        if concepts_db.get(subj_name, {}).get("type") != "subject":
            continue
        if concepts_db.get(act_name, {}).get("type") != "action":
            continue
        # negations, questions and conditionals do not ASSERT the
        # fact ("dogs don't fly", "can a dog fly?") -> they are not pairs.
        from core.contradiction_rules import is_non_assertive
        if is_non_assertive(tok.head):
            continue
        pairs.append((subj_name, act_name))
    return pairs


def _resolve_host_identity_value(property_name, default=None):
    """
    Reads the character's real identity value straight from
    motors.core_identity.CORE_RULES -- imported at call time (not at
    module load) so this always reflects whatever character.json was
    injected for the current run, never a stale copy.
    """
    try:
        from motors.core_identity import CORE_RULES
    except Exception:
        return default
    for rule in CORE_RULES.values():
        if rule.get("type") == "identity":
            return rule.get("value", {}).get(property_name, default)
    return default


def detect_identity_contradiction(raw_text):
    """
    Paper §4.4 "Identity verification" dual-check (CCM_paper_v1.pdf,
    2026-09-18): a claim about the host's own identity gets checked
    against Core Identity's narrative values -- e.g. "YOU ARE 40 YEARS
    OLD" when Core Identity says 25 -> mismatch -> correction "I AM 25
    YEARS OLD".

    NOTE: the paper's own pseudocode reads this as
    `internal_subject.related["age"] = 25`, as if ConceptsDB stored the
    actual value. It doesn't -- every node's `related` only holds
    somatic/mental ACTIVATION TAGS, never factual values (see any node
    in db_concepts.py). The real factual values live in
    motors/core_identity.py::CORE_RULES[...]["value"], so that's what
    this checks against instead -- same two-source spirit as the paper
    (an associative/grammar check + a narrative-facts check), adapted to
    how this codebase actually stores identity.

    Scoped for now to numeric age claims -- the paper's own worked
    example, and the one claim type that is unambiguous to compare
    ("your name is X" has no single correct paraphrase to detect a claim
    text was even making an assertion vs. a question; a numeric "X
    years old" reliably does). Extending to other identity properties
    (height, etc.) is a separate, later addition, not touched here.
    """
    if not raw_text:
        return {"is_contradiction": False}
    try:
        from core.construction_matcher import get_nlp
        from db.db_concepts import resolve_concept
    except Exception:
        return {"is_contradiction": False}
    try:
        doc = get_nlp()(raw_text)
    except Exception:
        return {"is_contradiction": False}

    for tok in doc:
        if not tok.like_num:
            continue
        try:
            claimed = int(float(tok.text))
        except ValueError:
            continue
        # Only treat it as an age claim when "year(s) [old]" sits near
        # the number -- otherwise a stray number in the scene (a price,
        # a distance) would false-positive as an age claim.
        window = doc[max(0, tok.i - 1): min(len(doc), tok.i + 4)]
        if not any(t.lemma_ == "year" for t in window):
            continue
        # Must actually be claimed ABOUT the host: some token in the
        # same sentence resolves to the external_subject ("you") concept.
        sent = tok.sent
        about_host = any(resolve_concept(t.lemma_ or t.text) == "you" for t in sent)
        if not about_host:
            continue
        real_age = _resolve_host_identity_value("age")
        if real_age is None:
            continue  # this character's identity doesn't define an age -- nothing to check
        try:
            if int(real_age) == claimed:
                continue  # claim matches -- not a contradiction
        except (TypeError, ValueError):
            continue
        return {
            "is_contradiction":   True,
            "contradiction_type": "identity",
            "property":           "age",
            "claimed_value":      claimed,
            "real_value":         real_age,
        }
    return {"is_contradiction": False}


def detect_contradiction(concept_names, concepts_db=None, raw_text=""):
    """
    CRITERION CHANGED 2026-09-19 (blacklist, see core/contradiction_rules.py):
    a contradiction is NO longer flagged because "the verb is not in related" (whitelist;
    it gave 9/20 false positives on normal roleplay sentences).
    Now only a (subject, verb) pair is flagged that the text ASSERTS and that is
    a clear impossibility (e.g. land animal + "fly": "fish don't
    fly"). IMPLICIT_CAPABILITIES remains only as a historical reference.

    Previous criterion (whitelist): the action does NOT appear in the
    subject's related field (explicit) NOR in the
    generic capability set for its (type, subtype) (implicit — see
    IMPLICIT_CAPABILITIES above). Absent from BOTH -- absent link in the
    graph, per the paper's own "what has no relations has no existence
    within the system" rule.

    BUG FIX 2026-09-18: this used to pair EVERY subject present anywhere
    in the scene with EVERY action present anywhere in the scene (a flat
    cross-product over concept_names), regardless of whether the text
    actually claimed that subject performed that action. Two real false
    positives this produced: "a bandit steps out of the bushes, blade
    drawn" -> flagged (bandit, drawn) as a contradiction even though
    grammatically it's the BLADE that was drawn, not the bandit; "Tell
    me about Joaquin" -> flagged (joaquin, tell) even though "tell" is
    an instruction to the host, not a claim that Joaquin tells anything.
    Now, when `raw_text` is given, real (subject, verb) pairs come from
    spaCy's dependency parse (nsubj/nsubjpass -> its own head verb) via
    _grammatical_subject_verb_pairs() -- only pairs the text actually
    asserts get checked. Falls back to the old flat cross-product only
    when raw_text isn't available (keeps existing callers working, but
    inherits the same false-positive risk this fix addresses -- pass
    raw_text whenever it's on hand).

    2026-09-18 addition: also runs detect_identity_contradiction() first
    when raw_text is available (paper §4.4 "Identity verification" -- see
    that function's docstring). Purely additive and returns early only
    when it actually finds an identity mismatch; everything below (the
    subject/action check above) runs exactly as before otherwise.
    """
    if raw_text:
        identity_result = detect_identity_contradiction(raw_text)
        if identity_result.get("is_contradiction"):
            return identity_result

    if concepts_db is None:
        from db.db_concepts import CONCEPTS
        concepts_db = CONCEPTS

    from core.contradiction_rules import is_clearly_impossible

    def _hit(subj, act):
        return {
            "is_contradiction": True,
            "subject":          subj,
            "action":           act,
            "subject_label":    subj,
            "action_label":     act,
        }

    real_pairs = _grammatical_subject_verb_pairs(raw_text, concepts_db)
    if real_pairs is not None:
        for subj, act in real_pairs:
            if is_clearly_impossible(subj, act, concepts_db):
                return _hit(subj, act)
        return {"is_contradiction": False}

    # Without raw_text there is no way to know who does what. A verdict is only issued when
    # the pairing is unambiguous (1 subject and 1 action
    # in the scene); with more, the cross product would invent false pairs.
    subjects = [n for n in concept_names if concepts_db.get(n, {}).get("type") == "subject"]
    actions  = [n for n in concept_names if concepts_db.get(n, {}).get("type") == "action"]
    if len(subjects) == 1 and len(actions) == 1 and is_clearly_impossible(subjects[0], actions[0], concepts_db):
        return _hit(subjects[0], actions[0])

    return {"is_contradiction": False}


# ── PUBLIC API ───────────────────────────────────────────────────────────────

def pre_input_somatic(concept_names, memory=None):
    from db.db_somatic  import TAG_VALUES_SOMATIC, SOMATIC_KEYS, SOMATIC_MAX
    from db.db_concepts import CONCEPTS
    return _pre_input_semantic(concept_names, CONCEPTS, TAG_VALUES_SOMATIC, SOMATIC_KEYS, SOMATIC_MAX, memory, motor="somatic")


def pre_input_mental(concept_names, memory=None):
    from db.db_mental   import TAG_VALUES_MENTAL, MENTAL_KEYS, MENTAL_MAX
    from db.db_concepts import CONCEPTS
    return _pre_input_semantic(concept_names, CONCEPTS, TAG_VALUES_MENTAL, MENTAL_KEYS, MENTAL_MAX, memory, motor="mental")


def pre_input_receptor_somatic(receptor_type, value, zone=None):
    return _pre_input_receptor(receptor_type, value, zone)


def pre_input_receptor_mental(receptor_type, value, zone=None):
    return _pre_input_receptor_mental(receptor_type, value, zone)


def pre_input_receptor_both(receptor_type, value, zone=None):
    from db.db_receptors import lookup_receptor, lookup_receptor_weighted
    from systems.core_system import update_stat
    match = lookup_receptor_weighted(receptor_type, value, zone) if zone else lookup_receptor(receptor_type, value)
    if not match:
        return None
    update_stat(stat_key=match["stat"], value=value, label=match["label"],
                somatic=match["somatic"], mental=match["mental"])
    meta = {"_token": receptor_type, "_type": "receptor", "_label": match["label"],
            "_stat": match["stat"], "_pipeline": "receptor", "_zone": zone or "unspecified"}
    return {"somatic": {**match["somatic"], **meta}, "mental": {**match["mental"], **meta}}
