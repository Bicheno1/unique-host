# systems/calibration_system.py — UNIQUE HOST
#
# CALIBRATION SYSTEM
# ───────────────────
# WHY IT EXISTS
# The Primary Evaluator (core/pre_input.py) reads a scene's concepts as one
# blended vector (focus + semi-foci). That works for "how dangerous does
# this scene feel", but it has no notion of WHO an event happens TO. "The
# monster attacks Joaquin" and "the monster dies" both just add more raw
# danger to the pile -- there is no way for a bad thing happening to a
# GOOD entity (a companion) to read differently from the same bad thing
# happening to a BAD entity (the monster itself, i.e. the threat being
# neutralized).
#
# WHAT IT DOES
# Any concept whose type is "subject" AND that already has a real baseline
# vector (a hand-authored node, a db_danger.py template, or a compiled
# character's identity-anchor "self" branch -- see character/injector.py)
# is a trackable ENTITY. The system keeps a running net position for each
# entity on the two orientation axes from the paper (section 1.4):
#   vi = V - I    (viability net,  north/south)
#   lg = Lv - Gv  (scope net,      east/west)
# and the mental mirror (pi = P - A, re = Er - Rr).
#
# When an event (the rest of the scene's concepts, e.g. "attacks"/"dies")
# co-occurs with a tracked entity, the event's own net is applied to that
# entity's net with a SIGN-RELATIVE rule instead of a plain sum:
#   - opposite signs (a viable/positive entity meets a danger event, or a
#     dangerous/negative entity meets a benefit event): normal addition --
#     the event pulls the entity's net toward (or across) zero and beyond.
#   - same sign (a dangerous/negative entity meets ANOTHER danger event --
#     e.g. the monster, already net-negative, "dies", another net-negative
#     event): the two cancel toward zero instead of stacking. A threat
#     source being destroyed reduces ITS OWN inviability; it does not add
#     a second dose of danger on top. The magnitude never crosses zero in
#     one event (clamped), so a partial hit still leaves some residual
#     charge -- "calmer, but still shaking", not an instant full flip.
#
# The DELTA (new net - old net) for each affected entity, summed across
# every entity present this cycle, is what gets fed back into the scene's
# push -- see motors/cycle_manager_v5.py, where entities are pulled OUT of
# the normal focus/semi-focus blend (so they don't ALSO contribute their
# raw average on top of this) and re-injected only through this system.

from db.db_somatic import SOMATIC_KEYS
from db.db_mental  import MENTAL_KEYS

# Verbs whose OWN concept carries one of these templates (db_danger.py) are
# inherently harm-denoting even when used intransitively ("the monster
# DIES" -- no direct object, the subject IS the one harmed). A verb not in
# this list only marks its object/passive-subject as affected (see
# find_affected_entities) -- an ordinary transitive verb doesn't turn its
# subject into a victim just because it has a grammatical object.
_INTRANSITIVE_HARM_TEMPLATES = {"mortal", "violence", "injury", "hazard"}

# Predicate adjectives ("Joaquin is DEAD/HELPLESS/TRAPPED") describe a
# state, not a verb -- dep_ "acomp"/"attr" -- so the dobj/nsubjpass/nsubj
# check above misses them entirely (no dependency runs through a real verb
# of harm). Small, curated, easy to extend; deliberately NOT a database
# change -- this is routing, not calibration content.
_HARM_ADJECTIVES = {
    "dead", "wounded", "hurt", "injured", "unconscious", "trapped",
    "helpless", "dying", "defenseless", "paralyzed", "broken", "bleeding",
}


def _has_real_event_push(concept: dict) -> bool:
    """True only for a genuine, hand-authored event push -- NOT the
    generic per-character slider every compiled character.json adds to
    almost every word via the questionnaire (fullcompiler/questionnaire/
    tree_questionnaire.py / questionnaire.py): those always sit under the
    literal key "valence" or a "shared__<category path>" key, and their
    tags are always named "valence__<word>". After a real character.json
    is injected (character/injector.py merges concepts_seed on top of the
    base ConceptsDB), a concept like "remember" or "thank" -- which the
    ENGINE never hand-authored any push for -- picks up exactly one of
    these generic branches and would otherwise look identical to a real
    event concept ("attack", "wound", "love"...) to a plain `if
    concept.get("related")` check. This walks past the generic branches
    and only returns True if at least one relation key is NOT "valence"/
    "shared__*" and carries at least one tag that isn't itself a generic
    "valence__*" placeholder.
    """
    related = concept.get("related") or {}
    for key, branches in related.items():
        if key == "valence" or key.startswith("shared__"):
            continue
        tags = list(branches.get("somatic", [])) + list(branches.get("mental", []))
        if any(not t.startswith("valence__") for t in tags):
            return True
    return False


def find_affected_entities(raw_text, concepts_db):
    """Grammatical rule (see module docstring): the Calibration System only
    applies to an entity when an event happens TO it this turn, not merely
    because it is present or because IT is the one acting. Returns the set
    of concept names that are:
      - the direct object or passive subject of any verb ("the monster
        ATTACKS JOAQUIN" -> joaquin; "JOAQUIN is attacked" -> joaquin), or
      - the subject of a verb that is itself inherently harm-denoting even
        without an object ("the MONSTER dies").
    A concept that is only ever a bare grammatical subject of an ordinary
    verb ("a MONSTER appeared", "the MONSTER attacks Joaquin" -- monster
    here is the agent, not the patient) is NOT affected: it stays on the
    normal focus/semi-focus path instead of going through calibration.
    Returns an empty set (not None) if raw_text is empty or spaCy isn't
    available -- callers then simply calibrate nothing this turn.
    """
    affected = set()
    if not raw_text:
        return affected
    try:
        from core.construction_matcher import get_nlp
        from db.db_concepts import resolve_concept
    except Exception:
        return affected
    try:
        doc = get_nlp()(raw_text)
    except Exception:
        return affected

    for tok in doc:
        # Predicate adjectives ("Joaquin is DEAD/HELPLESS") -- checked
        # BEFORE the resolve_concept() gate below, because the adjective
        # itself ("helpless") often isn't in the concept lexicon at all;
        # only its SUBJECT needs to resolve. tok here IS the adjective.
        if tok.dep_ in ("acomp", "attr") and tok.lemma_.lower() in _HARM_ADJECTIVES:
            for sib in tok.head.children:
                if sib.dep_ in ("nsubj", "nsubjpass"):
                    subj_name = resolve_concept(sib.lemma_)
                    if subj_name:
                        affected.add(subj_name)
            continue

        name = resolve_concept(tok.lemma_)
        if not name:
            continue
        if tok.dep_ in ("dobj", "nsubjpass"):
            # FIX: this branch used to add the entity unconditionally --
            # any transitive verb with the entity as object counted as
            # "something happened to it", including verbs with no real
            # semantic push at all ("Do you REMEMBER the monster?",
            # "Joaquin THANKS the monster", "Joaquin SEES the monster").
            # Those aren't events that change the entity's own state; they
            # let a cognitive/speech verb's leftover scene words (whatever
            # else pre_input finds once the entity itself is excluded --
            # "do"/"you"/etc.) get fed into calibrate() as if they were the
            # verb's own push, producing large, ungrounded swings (see
            # conversation: "remember" sent monster's V from 0 to 112 in
            # one turn). Now the governing verb must itself carry a real
            # push -- either a hand-authored `related` field (covers
            # harmful verbs like attack/wound/kill/hurt AND genuinely
            # positive ones like love/heal, anything with its own
            # somatic/mental tags) or an `intrinsic_danger` template
            # (db_danger.py verbs that only carry that flag) -- before the
            # entity is treated as affected. A verb absent from ConceptsDB,
            # or present with no related content and no danger template,
            # leaves the entity on the normal focus/semi-focus path
            # instead, same as if it had merely been mentioned.
            verb_name = resolve_concept(tok.head.lemma_)
            verb_c = concepts_db.get(verb_name, {}) if verb_name else {}
            if verb_c.get("intrinsic_danger") or _has_real_event_push(verb_c):
                affected.add(name)
        elif tok.dep_ == "nsubj":
            # A verb with its OWN direct object/passive-subject already has
            # a real patient -- don't ALSO treat its subject/agent as
            # affected just because the verb is harm-tagged ("the monster
            # ATTACKS Joaquin" -- monster is the agent, Joaquin (dobj) is
            # the one affected, not both).
            has_own_object = any(c.dep_ in ("dobj", "nsubjpass") for c in tok.head.children)
            if has_own_object:
                continue
            verb_name = resolve_concept(tok.head.lemma_)
            verb_c = concepts_db.get(verb_name, {}) if verb_name else {}
            if verb_c.get("intrinsic_danger") in _INTRANSITIVE_HARM_TEMPLATES:
                affected.add(name)
    return affected


def _net_pair(vec, keys, pos_key, neg_key):
    """(pos - neg) from a {V,I,Lv,Gv}-or-{P,A,Er,Rr}-shaped vector. Missing keys read as 0."""
    if not vec:
        return 0.0
    return float(vec.get(pos_key, 0.0)) - float(vec.get(neg_key, 0.0))


def _split_net_delta(delta, pos_key, neg_key):
    """Turns a signed net delta back into a {pos_key, neg_key} contribution.
    A positive delta (net moved toward viable/local) lands entirely on
    pos_key; a negative delta (net moved toward inviable/global) lands
    entirely on neg_key -- mirrors how the paper's orientation collapses
    a signed value back into the two non-negative magnitudes it came from.
    """
    if delta >= 0:
        return {pos_key: delta, neg_key: 0.0}
    return {pos_key: 0.0, neg_key: -delta}


def calibrate(old_net: float, event_net: float) -> float:
    """The core rule (see module docstring). Both 0 or event_net == 0 -> no-op."""
    if old_net == 0.0 or event_net == 0.0:
        return old_net + event_net
    if (old_net > 0) == (event_net > 0):
        # same orientation -- cancel toward zero, never cross it in one event
        magnitude = max(0.0, abs(old_net) - abs(event_net))
        return magnitude if old_net > 0 else -magnitude
    # opposite orientation -- ordinary additive combination
    return old_net + event_net


def _apply_net_delta(pos, neg, new_net):
    """Moves a (pos, neg) pair to match a newly-calibrated net, WITHOUT
    collapsing the pair down to one side. The pair's total magnitude
    (pos + neg) is preserved as much as possible -- only the excess needed
    to reach new_net is drained from whichever side must shrink, so an
    entity that is mostly-dangerous-but-a-little-viable keeps looking that
    way instead of turning into pure zero-or-other-extreme. This is what
    keeps a single entity's push comparable in scale to what its own raw
    tag average used to contribute directly (before entities were pulled
    out of the normal focus/semi-focus blend) -- collapsing to a bare net
    and dumping it on one side understates real magnitude and was found to
    let an unrelated chemical-feedback pathway tip the category the wrong
    way on later turns (see conversation).
    """
    old_net = pos - neg
    delta = new_net - old_net
    if delta > 0:
        # net moves toward the positive side: drain neg first, spill any
        # remainder onto pos so no magnitude is silently lost
        drain = min(neg, delta)
        neg -= drain
        pos += (delta - drain)
    elif delta < 0:
        drain = min(pos, -delta)
        pos -= drain
        neg += (-delta - drain)
    return pos, neg


class CalibrationSystem:
    """Tracks per-entity net position across a scene/session. One instance
    per character (per CycleManagerV5), living for as long as the character
    does -- entities persist between turns like everything else in the
    engine, so a companion who was hurt earlier stays "shaken" going in.
    """

    def __init__(self):
        self.entities = {}      # name -> {"vi":.., "lg":.., "vi_m":.., "lg_m":..}
        self._not_trackable = set()   # concepts checked and found to have no baseline -- cache

    # ── entity recognition & seeding ────────────────────────────────────
    def is_entity(self, name, concepts_db) -> bool:
        if name in self.entities:
            return True
        if name in self._not_trackable:
            return False
        c = concepts_db.get(name)
        if not c or c.get("type") != "subject":
            self._not_trackable.add(name)
            return False
        if not self._seed(name, concepts_db):
            self._not_trackable.add(name)
            return False
        return True

    def _seed(self, name, concepts_db) -> bool:
        from core.pre_input import _concept_value
        from db.db_somatic import TAG_VALUES_SOMATIC
        from db.db_mental  import TAG_VALUES_MENTAL
        base_s = _concept_value(name, concepts_db, TAG_VALUES_SOMATIC, SOMATIC_KEYS, motor="somatic")
        base_m = _concept_value(name, concepts_db, TAG_VALUES_MENTAL,  MENTAL_KEYS,  motor="mental")
        if base_s is None and base_m is None:
            return False   # no real baseline anywhere -- not a trackable entity, just scenery
        base_s = base_s or {}
        base_m = base_m or {}
        # Full vector, NOT a collapsed net -- see _apply_net_delta docstring
        # for why: an entity keeps pushing its real V AND I (both sides),
        # not just their difference, so a single entity's push stays
        # comparable in scale to what its raw tag average used to
        # contribute before entities were pulled out of the normal blend.
        self.entities[name] = {
            "V":  float(base_s.get("V", 0.0)),  "I":  float(base_s.get("I", 0.0)),
            "Lv": float(base_s.get("Lv", 0.0)), "Gv": float(base_s.get("Gv", 0.0)),
            "P":  float(base_m.get("P", 0.0)),  "A":  float(base_m.get("A", 0.0)),
            "Er": float(base_m.get("Er", 0.0)), "Rr": float(base_m.get("Rr", 0.0)),
        }
        return True

    # ── applying an event to whichever entities are present ────────────
    def apply_event(self, entity_names, event_vec_s, event_vec_m, concepts_db):
        """entity_names: concepts this cycle that are_entity(). event_vec_s/m:
        the scene's push from everything ELSE (the non-entity concepts --
        e.g. "attacks"/"dies"). Returns (push_vec_s, push_vec_m): the
        combined contribution to feed back into the cycle, replacing what
        these entities' own raw averages would have added.

        Every entity present pushes its CURRENT full vector every cycle
        it's mentioned -- a monster sitting there being a monster is still
        a monster even on a turn with no separate event word ("a monster
        appeared"), so its baseline must keep pushing on its own, not only
        on the turn something happens to it. When an event vector IS
        present this cycle, the entity's current vector is first updated
        by the calibration rule (see module docstring) on each axis pair's
        NET, then redistributed onto that pair without losing magnitude
        (_apply_net_delta), so what pushes this turn already reflects
        anything that just happened to it.
        """
        push_s = {k: 0.0 for k in SOMATIC_KEYS}
        push_m = {k: 0.0 for k in MENTAL_KEYS}
        if not entity_names:
            return push_s, push_m

        has_event  = bool(event_vec_s) or bool(event_vec_m)
        event_vi   = _net_pair(event_vec_s, SOMATIC_KEYS, "V", "I")
        event_lg   = _net_pair(event_vec_s, SOMATIC_KEYS, "Lv", "Gv")
        event_vi_m = _net_pair(event_vec_m, MENTAL_KEYS, "P", "A")
        event_lg_m = _net_pair(event_vec_m, MENTAL_KEYS, "Er", "Rr")

        for name in entity_names:
            if not self.is_entity(name, concepts_db):
                continue
            e = self.entities[name]
            if has_event:
                new_vi   = calibrate(e["V"] - e["I"],   event_vi)
                new_lg   = calibrate(e["Lv"] - e["Gv"], event_lg)
                new_vi_m = calibrate(e["P"] - e["A"],   event_vi_m)
                new_lg_m = calibrate(e["Er"] - e["Rr"], event_lg_m)
                e["V"],  e["I"]  = _apply_net_delta(e["V"],  e["I"],  new_vi)
                e["Lv"], e["Gv"] = _apply_net_delta(e["Lv"], e["Gv"], new_lg)
                e["P"],  e["A"]  = _apply_net_delta(e["P"],  e["A"],  new_vi_m)
                e["Er"], e["Rr"] = _apply_net_delta(e["Er"], e["Rr"], new_lg_m)

            for k in SOMATIC_KEYS:
                push_s[k] += e[k]
            for k in MENTAL_KEYS:
                push_m[k] += e[k]

        return push_s, push_m
