# motors/cycle_manager_v5.py — CCM v5
#
# ORCHESTRATOR — coordinates the 4 motors in sequence
#
# FULL FLOW:
#
#  SOMATIC EXTERNAL ←ping-pong→ MENTAL EXTERNAL
#         ↓                            ↓
#   somatic_engine              mental_engine
#         ↓     ←cross-recal→         ↓
#              state (D, C)
#                   ↑↓
#  SOMATIC INTERNAL    MENTAL INTERNAL
#  (reflexes, vital)   (evocation, reflexes)
#         ↓                    ↓
#    amplifies/contains the state
#         ↓
#    story_modifier learns
#    memory registers
#    output_checker decides which dominates

from engines.somatic_engine import SomaticEngine
from engines.mental_engine   import MentalEngine
from systems.memory_system   import MemorySystem
from systems.chemical_system     import ChemicalSystem
from systems.mental_state_system import MentalStateSystem

from motors.external_mental  import process as ext_mental_process, resolve_text
from motors.internal_somatic import process as int_somatic_process
from motors.internal_mental  import process as int_mental_process
from motors.vitality_stats   import VitalityStats
from motors.core_identity    import consult as core_consult, apply as core_apply, IdentityAnchorSystem

from db.db_somatic import SOMATIC_KEYS
from db.db_mental  import MENTAL_KEYS
from layers.quadrant_reader import read_somatic_sector, read_mental_sector
from layers.emotion_mapper  import get_emotion, get_somatic_state
from layers.processing_mode import get_processing_mode
from systems.plasticity_system import apply_plasticity, OPENING_WINDOW_CYCLES
from core.formulas import calculate_D, calculate_C, calculate_df
import math


def _get_processing_mode_info(cfx: float, m_dist: float) -> dict:
    """Helper — derives tension label and calls get_processing_mode."""
    from output.output_layer import get_tension_mental
    tension = get_tension_mental(m_dist)
    return get_processing_mode(cfx, tension)

class CycleManagerV5:
    def __init__(self):
        # State engines
        self.somatic    = SomaticEngine()
        self.mental     = MentalEngine()

        # Stats systems
        self.vitality   = VitalityStats()
        self.identity_anchor_system = IdentityAnchorSystem()
        from motors.internal_mental import MentalEvocation
        self.mind_evocation = MentalEvocation()

        # Separate memories (somatic and mental)
        self.memory_s   = MemorySystem()
        self.memory_m   = MemorySystem()

        # Chemicals (complementary somatic internal)
        self.chemicals     = ChemicalSystem()

        # Primary Evaluator category bias — 4 questions (one per category),
        # separate from the chemicals' 16 per-axis gain questions. See
        # core/response_matrix.py DEFAULT_CATEGORY_BIAS. Neutral (5/10 on
        # all 4) until character/injector.py sets it from character.json.
        from core.response_matrix import DEFAULT_CATEGORY_BIAS
        self.category_bias = dict(DEFAULT_CATEGORY_BIAS)
        # Mental twin — Primary Evaluator category bias for
        # the mental side, separate from the somatic one (same neutral default
        # until injector.py loads it from the questionnaire).
        self.mental_category_bias = dict(DEFAULT_CATEGORY_BIAS)

        # mental states (complementary mental internal)
        self.mental_states = MentalStateSystem()

        self._last_concepts = []

        # Last sentence variant used per mode (core/response_bank.py) —
        # per session, not global, so two characters don't step on each other.
        self._variant_memory = {}

        # Same idea, separate dict, for the <<...>> gesture bank
        # (core/action_bank.py) — kept apart from _variant_memory above so
        # the dialogue line and the action line don't repeat-block each
        # other under the same mode key (they're picked independently).
        self._action_variant_memory = {}

        # Character name -- used by core/construction_matcher.py
        # so it isn't confused with the danger/benefit subject when
        # parsing the raw input. Set by
        # character/injector.py from character.json["identity"]["name"].
        self.character_name = None

        # Who the person on the other side of the screen is playing (set by the UI).
        # When set, every event stored in memory is tagged with it, so the host can
        # answer "What do you think about me?" (core/memory_recall.py).
        self.user_name = None
        self._present_name = None      # who is talking to the host THIS turn (see process(speaker=...))
        self._recall_last = {}
        self._last_claim = None

    # ──────────────────────────────────────────────
    # MAIN CYCLE
    # ──────────────────────────────────────────────

    def process(self, text: str = "", marked_input: dict = None,
                speaker: str = "narrator") -> dict:
        """
        Main entry point.

        text         : raw fallback text (legacy / demo use) OR a full
                       marked-syntax message ('"scared" stay back <<a
                       bandit blocks the road>>') -- auto-detected below.
        marked_input : {"emotion": str|None, "dialogue": str|None, "action": str|None}
                       output of the Marker Parser (quotes / plain text / <<...>>).
                       Pass this directly if the caller already parsed it.
        speaker      : 2026-09-09, "who's talking" selector -- an open,
                       growing list, not just two fixed roles. "narrator"
                       (default) means this turn describes the WORLD
                       ("a bandit blocks the road"): the focus is parsed
                       from the text as before. Anything else -- "user",
                       "bandit", a proper name -- means the speaker's
                       identity IS the focus already (no parsing needed
                       to know who's being reacted to): the character
                       just said/did something TO Delia directly, and
                       both the dialogue's grammatical subject and the
                       action's target lock onto that name instead of
                       whatever construction_matcher would've guessed
                       from the sentence. See core/construction_matcher.py
                       :speaker_to_focus() for the article/capitalization
                       rules (e.g. "user" stays bare, "bandit" -> "the
                       bandit", "Mark" stays as-is).

        FIX 2026-09-09 (found testing the REAL input/output contract from
        the system-state notes §3 -- "in like this, out like this", not the
        legacy flat-string demo path): two gaps closed, both real, found
        by actually calling process(marked_input=...) with no `text` and
        watching the sentence-quality fixes from the previous session go
        dark --
          1. `text` and `marked_input` never talked to each other: a
             caller using ONLY marked_input got an empty `raw_text` at
             _build_output() (that param was always the literal `text`
             arg), so construction_matcher.analyze_input() never even
             ran and every response fell back to the bare "that" --
             confirmed: {"emotion":"scared","dialogue":"stay back",
             "action":"a bandit blocks the road"} produced "I suppress
             that, plain and simple." instead of "...the bandit."
          2. A caller passing the FULL marker-syntax string as `text`
             ('"scared" stay back <<...>>') got it pooled as one literal
             blob of concept tokens (quotes/angle-brackets and all) --
             it was never actually run through marker_parser.py despite
             that being the documented real input contract.
        Fix: `text` is now auto-detected for marker syntax up front (via
        the SAME core/marker_parser.py already built and tested) --  if
        found, it's split into `marked_input` and cleared to avoid double-
        pooling. Either way, `raw_text` for the grammar/construction
        pipeline is now built from dialogue+action (the fragments that
        can actually contain a real sentence -- emotion is normally a
        bare mood tag, not something to extract a grammatical subject
        from), joined as separate sentences so spaCy doesn't fuse them
        into one run-on clause.
        """
        from core.marker_parser import parse_marked_input
        from core.construction_matcher import speaker_to_focus

        if marked_input is None:
            auto_parsed = parse_marked_input(text)
            if auto_parsed["emotion"] or auto_parsed["action"]:
                # real marker syntax was present in `text` -- use the
                # parsed fragments as the source of truth, don't also
                # pool the original raw string (that would double-count
                # the dialogue fragment already inside auto_parsed).
                marked_input = auto_parsed
                text = ""
            else:
                marked_input = {}
        else:
            marked_input = marked_input or {}

        forced_focus = speaker_to_focus(speaker)
        self._last_speaker = speaker
        # Who is "present" for memory: a NAMED speaker ("Joaquin", "bandit") is the one talking to the
        # host, so events are tagged with that name and "What do you think about me?" is about them.
        # For the narrator / "user" speakers it is the name the player gave (user_name), if any.
        _sp = (speaker or "narrator").strip().lower()
        if _sp in ("narrator", "user", ""):
            self._present_name = self.user_name.lower() if self.user_name else None
        else:
            self._present_name = _sp


        # ── STEP 1: EXTERNAL MOTORS ────────────────────────────
        # Resolve concepts from the pooled text (emotion + dialogue + action + legacy text)
        import re
        from db.db_concepts import resolve_concept
        STOPWORDS = {"a","an","the","in","on","at","is","are","was","i","and","or","of"}

        pooled_text = " ".join(
            v for v in (marked_input.get("emotion"),
                        marked_input.get("dialogue"),
                        marked_input.get("action"),
                        text) if v
        )

        # Fix: only matches clean lexicon keys ("monster",
        # "father", "what", "name"), but this tokenizer was a bare
        # `.split` with NO punctuation stripping at all -- real
        # dialogue is full of trailing punctuation ("monster!",
        # "name?") and possessives ("father's", "what's"), and every
        # single one of those tokens silently resolved to nothing.
        # Confirmed via direct resolve_concept calls: "monster!" ->
        # None but "monster" -> "monster"; "father's" -> None but
        # "father" -> "father"; same for "what's"/"what" and
        # "name?"/"name". This was quietly eating a huge fraction of
        # ordinary questions and exclamations, not an edge case.
        # Two-step clean per token: drop a trailing possessive "'s"
        # first (so "father's" -> "father", not "fathers"), then strip
        # any remaining non-word characters (quotes, "!?.,:;" etc).
        # Broader contractions ("don't", "can't") aren't specifically
        # handled here -- that's a separate concern (they'd need actual
        # expansion, "do not"/"can not", not just punctuation
        # stripping) left for another session if it turns out to matter.
        def _clean_token(tok: str) -> str:
            tok = re.sub(r"'s$", "", tok)
            return re.sub(r"[^\w]", "", tok)

        tokens = [_clean_token(t) for t in pooled_text.lower().split()]
        tokens = [t for t in tokens if t and t not in STOPWORDS]
        concept_names = []
        for token in tokens:
            name = resolve_concept(token)
            if name and name not in concept_names:
                concept_names.append(name)

        self._last_concepts = concept_names

        # Grammar-pipeline text (construction_matcher.py/spaCy) -- built
        # from whichever fragments can actually contain a real sentence
        # to extract a subject from. Joined as separate sentences ("."
        # between them) so spaCy's sentencizer doesn't fuse "stay back"
        # and "a bandit blocks the road" into one run-on clause.
        grammar_fragments = [f for f in (marked_input.get("dialogue"),
                                          marked_input.get("action"),
                                          text) if f]
        raw_text = ". ".join(grammar_fragments)


        # Fix: # detect_contradiction used to run inside _build_output,
        # i.e. AFTER STEP 9's apply_plasticity already ran THIS same
        # cycle. Relational dissociation (systems/plasticity_system.py)
        # can legitimately strip a concept's "related" link when its
        # activation diverges from a related concept's beyond
        # RELATED_THRESHOLD -- and when the stripped link happened to be
        # a real capability (e.g. "bird" -> "fly"), detect_contradiction
        # saw it ALREADY GONE and flagged a true statement as false
        # ("a bird flies" -> "You not fly bird"). Root fix: capture the
        # contradiction reading HERE, right after concepts resolve and
        # before anything this cycle has a chance to mutate CONCEPTS --
        # not a patch on the symptom, moving the read to before the
        # write that was racing it.
        from core.pre_input import detect_contradiction
        import db.db_concepts as db_concepts
        # now also passes raw_text so detect_contradiction can
        # use real spaCy subject-verb pairs instead of pairing every
        # subject in the scene with every action in the scene (see the
        # BUG FIX note in pre_input.py:detect_contradiction docstring).
        contradiction_info = detect_contradiction(concept_names, db_concepts.CONCEPTS, raw_text=raw_text) if concept_names else {"is_contradiction": False}

        # MEMORY CLAIMS ( core/memory_claims.py): what the user says about the
        # past is compared with the stored events. A mismatch becomes a contradiction
        # (same channel as the identity/age check); a match or an "I don't remember"
        # is answered as a recall in _build_output.
        from core.memory_claims import check_claim
        self._last_claim = check_claim(self, raw_text, concept_names) if concept_names else None
        if self._last_claim and self._last_claim["kind"] == "contradiction" \
                and not contradiction_info.get("is_contradiction"):
            contradiction_info = {"is_contradiction": True, "contradiction_type": "memory",
                                  "phrase": self._last_claim["phrase"],
                                  "subject_label": self._last_claim["subject"], "action_label": None}

        # Pre-input semantic → vectors for both external motors
        # Somatic weight comes mainly from the <<action>> fragment;
        # mental weight comes mainly from "emotion" + dialogue.
        # TODO: split concept_names by originating fragment
        # once the Format Matcher assigns per-slot weighting.
        from core.pre_input import pre_input_somatic, pre_input_mental
        vec_s = pre_input_somatic(concept_names, memory=self.memory_s) if concept_names else None
        vec_m = pre_input_mental(concept_names,  memory=self.memory_m) if concept_names else None

        # Lexicon bridge — real (not hand-authored-concept) words with
        # actual axis signal (see core/lexicon_bridge.py docstring for
        # exactly which ~120 valence words + scope-classified adjectives
        # carry real data today). Independent of db_concepts.py; combined
        # additively in oriented space via apply_input() so a scene with
        # BOTH a hand-authored concept (e.g. "ghost") and a lexicon word
        # (e.g. "never") reads both at once.
        from core.lexicon_bridge import lexicon_axis_push
        from core.formulas import apply_input
        lex_push = lexicon_axis_push(tokens) if tokens else None
        if lex_push:
            if vec_s:
                vec_s = apply_input(vec_s, lex_push, SOMATIC_KEYS)
            else:
                vec_s = lex_push

        # Internal activations from the graph → chemicals
        from db.db_concepts import get_internal_activations
        somatic_acts, mental_acts = get_internal_activations(concept_names) if concept_names else ({}, {})

        # ── STEP 1.5: TAG SCALER ──────────────────────────────
        # Scales the vector according to current engine distance.
        # If the host is already tense → new input hits harder.
        # Simulates intoxication, trauma, altered states.
        from layers.tag_scaler import scale_tag
        # Raw input vectors BEFORE the state-dependent scaling: the memory system's THREAT signal is
        # measured on them (paper orientation: inviability I counts against V, absence A against P), so
        # it depends on what the input is and not on how pinned the engine already is.
        _raw_s = dict(vec_s) if vec_s else None
        _raw_m = dict(vec_m) if vec_m else None
        from core.formulas import get_rhomboid_center
        import math
        if vec_s:
            s = self.somatic.current_state()
            scx, scy = get_rhomboid_center(s, SOMATIC_KEYS)
            s_dist = math.sqrt(scx**2 + scy**2)
            vec_s = scale_tag(vec_s, s_dist, SOMATIC_KEYS)
        if vec_m:
            m = self.mental.current_state()
            mcx, mcy = get_rhomboid_center(m, MENTAL_KEYS)
            m_dist = math.sqrt(mcx**2 + mcy**2)
            vec_m = scale_tag(vec_m, m_dist, MENTAL_KEYS)

        # ── step 2: CORE IDENTITY filters external vectors ─────
        core_active = core_consult(concept_names) if concept_names else []

        if vec_s and core_active:
            vec_s = core_apply(vec_s, SOMATIC_KEYS, core_active)
        if vec_m and core_active:
            vec_m = core_apply(vec_m, MENTAL_KEYS, core_active)

        # ── step 3: VITALITY TICK ──────────────────────────────
        self.vitality.tick(active_concepts=concept_names)
        self.identity_anchor_system.tick(concept_names, self.vitality)
        vital_s, vital_m = self.vitality.get_pressure()

        # ── STEP 4: CHEMICALS + MENTAL STATES ────────────────────
        # Bug C: process_triggers -- LEGACY_MODE_TRIGGERS --
        # compared the word's name against fixed lists (e.g. "calm"
        # triggered accept/investigate/deny/cooperate/signal AT ONCE, with
        # flat +1.0 every cycle, no gain, no gate) and NEVER returned to
        # rest as long as the word stayed in the scene -- see
        # conversation release_from_axis_push (below) already
        # covers the same concepts, including hand-authored ones like
        # "ghost", via the real formula (tags -> geometry -> category ->
        # questionnaire gain), so removing this line loses no
        # coverage -- it only removes the broken shortcut.
        # self.chemicals.process_triggers(concept_names, vitality_stats=self.vitality.all_needs)
        # Formula path: works for ANY concept, including the ~5,000 in
        # db/db_lexicon.py that have no hand-written triggers list —
        # resolves which of the 16 matrix modes wins this cycle (category
        # row from the Primary Evaluator × axis from this scene's raw push
        # vec_s, gain-weighted per character). See
        # systems/chemical_system.py:release_from_axis_push and
        # core/response_matrix.py:primary_evaluator_category.
        if vec_s:
            from core.response_matrix import primary_evaluator_category_from_axis_push
            category = primary_evaluator_category_from_axis_push(
                {k: vec_s[k] for k in SOMATIC_KEYS}, category_bias=self.category_bias
            )
            release_result = self.chemicals.release_from_axis_push(
                category, {k: vec_s[k] for k in SOMATIC_KEYS}, somatic_dist=s_dist
            )
        else:
            # without vec_s there is no raw reading to categorize -- neutral
            # (same behavior as an even category_bias, see
            # DEFAULT_CATEGORY_BIAS)
            category = "neutral"
            release_result = None

        # THREAT signal for the memory system: NET inviability (I - V) and NET absence
        # (A - P) of the raw input, 0 when the input is viable/present. A flat vector (birds sing:
        # V=I=Lv) gives ~0 and a winning-axis test would flip on noise; the net does not.
        threat_s = max(0.0, _raw_s["I"] - _raw_s["V"]) if _raw_s else 0.0
        threat_m = max(0.0, _raw_m["A"] - _raw_m["P"]) if _raw_m else 0.0

        # Mental twin — same criterion as the block
        # above, on vec_m instead of vec_s. Before, this did not exist: the
        # mental side only had mental_states.process_triggers (fixed trigger-
        # word, no character gain). Now the formula path also runs,
        # with its own category_bias/gain (Mental
        # Chemistry questionnaire, see the compiler package's questionnaire/questionnaire.py).
        if vec_m:
            from core.response_matrix import primary_evaluator_category_from_axis_push as _pecap
            mental_category = _pecap(
                {k: vec_m[k] for k in MENTAL_KEYS}, keys=MENTAL_KEYS,
                category_bias=self.mental_category_bias,
            )
            self.mental_states.release_from_axis_push(
                mental_category, {k: vec_m[k] for k in MENTAL_KEYS}
            )

        # Emotion label ingredients ( fusion, see
        # systems/chemical_system.py get_emotion_label): same
        # (category, winning_axis) cell release_from_axis_push just
        # resolved, graded by its own magnitude through the existing
        # saturation ladder — "fear", "panic", "terror" etc. are the
        # SAME underlying decision, not a second system computed
        # separately.
        #
        # CHANGED (worried/valiant emotion review): the
        # actual word lookup moved to _build_output, AFTER Df/Cf are
        # known -- see the comment there for why. Only the raw
        # ingredients (winning_axis, axis_magnitude) are captured here,
        # same as before.
        winning_axis = axis_magnitude = None
        if release_result:
            winning_axis, axis_magnitude = release_result

        # Apply graph multipliers (adrenaline x2 → extra release)
        for tag, count in somatic_acts.items():
            if count > 1:
                self.chemicals.release(tag, amount=count - 1)
        chem_s = self.chemicals.get_somatic_push()

        # Mental states — mental analog of the chemicals
        self.mental_states.process_triggers(concept_names)
        chem_m = self.mental_states.get_mental_push()
        # Formula path — the push from the new matrix is added
        # to that of the old trigger words (chem_m), just like in the somatic side
        # where chem_s is already 100% formula-driven. Both coexist here
        # for now (see conversation: mental_states.py is still the old
        # system, not touched yet).
        matrix_m = self.mental_states.get_matrix_push()
        for k in MENTAL_KEYS:
            chem_m[k] = chem_m.get(k, 0.0) + matrix_m.get(k, 0.0)

        # ── STEP 5: STATE BEFORE (for plasticity) ─────────────
        state_before_s = dict(self.somatic.current_state())
        state_before_m = dict(self.mental.current_state())

        # ── STEP 6: PING-PONG EXTERNAL ──────────────────────────
        # Ping 1 — somatic receives external + internal pressure
        if vec_s:
            self.somatic.apply_external(vec_s)
        self.somatic.apply_internal(vital_s)
        self.somatic.apply_internal(chem_s)
        D1 = self.somatic.D()   # direct somatic impact

        # Ping 2 — mental receives external + D1 (cross)
        if vec_m:
            self.mental.apply_external(vec_m)
        self.mental.apply_internal(vital_m)
        self.mental.apply_internal(chem_m)
        self.mental.recalibrate(D1)
        C1 = self.mental.C()    # direct mental impact

        # Pong — somatic receives C1
        self.somatic.recalibrate(C1)
        D2 = self.somatic.D()   # direct somatic impact post-cross

        # Ping final — mental receives D2
        self.mental.recalibrate(D2)
        C2 = self.mental.C()    # direct mental impact post-cross

        # ── STEP 6.5: HOMEOSTATIC DECAY ────────────────
        dx2, dy2 = D2
        cx2, cy2 = C2
        s_intensity = math.sqrt(dx2**2 + dy2**2) / 100.0
        m_intensity = math.sqrt(cx2**2 + cy2**2) / 100.0
        decay_s = max(0.05, 0.20 - s_intensity * 0.10)
        decay_m = max(0.05, 0.20 - m_intensity * 0.10)
        self.somatic.decay_toward_base(rate=decay_s)
        self.mental.decay_toward_base(rate=decay_m)

        # ── STEP 7: INTERNAL MOTORS ────────────────────────────
        int_s = int_somatic_process(D2, self.vitality.all_needs(), chemical_system=self.chemicals)
        self.somatic.apply_internal(int_s)

        # Mental evocation — NEW (replaces the duplicated
        # passthrough of chem_m, see internal_mental.py). If any
        # mind_stat is in strong deficit, it looks for a real associated memory;
        # if it finds one it pushes lightly and decays fast (does not re-fire
        # until the cooldown has passed); if it finds nothing, it notes it in
        # last_unmet_needs so the output layer can verbalize it
        # ("I'm scared, could you hold me?" -- pending, not yet
        # implemented).
        from core.formulas import get_rhomboid_center as _grc_mental
        _mcx, _mcy = _grc_mental(self.mental.current_state(), MENTAL_KEYS)
        current_mental_distance = math.sqrt(_mcx**2 + _mcy**2)
        evocation_push = self.mind_evocation.tick(self.vitality, self.memory_m, current_mental_distance)
        int_m = int_mental_process(evocation_push)
        self.mental.apply_internal(int_m)

        # ── STEP 7.5: FINAL IMPACT (Df / Cf) ────────────────
        # D1/C1 = direct impact     — the raw hit
        # D2/C2 = relational impact — how it distributes across factors
        # Df/Cf = final impact      — median point D1↔D2, dampens without losing direction
        s_state_final = self.somatic.current_state()
        m_state_final = self.mental.current_state()
        Df = calculate_df(s_state_final, ["V", "I", "Lv", "Gv"])
        Cf = calculate_df(m_state_final, ["P", "A", "Er", "Rr"])

        # Chemicals + mental states decay
        self.chemicals.decay()
        self.mental_states.decay()
        self.mental_states.decay_matrix()

        # ── step 8: MIND STATS tick ────────────────────────────
        # (deleted self.mind.tick -- motors/mind_stats.py
        # was a duplicate of systems/vital_system.py:MENTAL_NEEDS that
        # never moved from its baseline. The real source already ticks by itself
        # inside self.vitality.tick, earlier in the cycle.)

        # ── STEP 9: STORY MODIFIER (plasticity) ────────────────
        plasticity = {}
        if concept_names:
            state_after_s = dict(self.somatic.current_state())
            state_after_m = dict(self.mental.current_state())
            state_after_m_tmp = dict(self.mental.current_state())
            from core.formulas import get_rhomboid_center as _grc
            import math as _math
            _cx, _cy = _grc(state_after_m_tmp, ["P","A","Er","Rr"])
            _dist_mental_now = _math.sqrt(_cx**2 + _cy**2)
            plasticity = apply_plasticity(
                concept_names, self.memory_m,
                state_before_s, state_after_s,
                state_before_m, state_after_m,
                dist_mental=_dist_mental_now,
                opening_allowed=self.memory_m.threat_recently(OPENING_WINDOW_CYCLES),
            )

        # ── STEP 10: MEMORY ───────────────────────────────────
        s_state = self.somatic.current_state()
        m_state = self.mental.current_state()

        # Memory logs the pooled fragments (not the possibly-now-empty
        # legacy `text`) so a marker-syntax turn still leaves a readable
        # short-term memory entry instead of "".
        _mem_concepts = list(concept_names)
        if self._present_name and self._present_name not in _mem_concepts:
            _mem_concepts.insert(0, self._present_name)       # first: survives the 5-concept cut
        _ign = {self._present_name} if self._present_name else set()
        self.memory_s.ignore_concepts = self.memory_m.ignore_concepts = _ign
        self.memory_s.update(pooled_text, _mem_concepts, s_state, m_state, threat_s, threat_m)
        self.memory_m.update(pooled_text, _mem_concepts, s_state, m_state, threat_s, threat_m)
        self._last_threat = {"somatic": round(threat_s, 1), "mental": round(threat_m, 1)}

        # ── STEP 11: OUTPUT ────────────────────────────────────
        return self._build_output(
            Df, Cf, D1, C1, core_active,
            int_s, int_m, plasticity,
            category, raw_text, winning_axis, axis_magnitude,
            contradiction_info, forced_focus=forced_focus,
        )

    # ──────────────────────────────────────────────
    # OUTPUT
    # ──────────────────────────────────────────────

    def _build_output(self, Df, Cf, D1, C1, core_active, int_s, int_m, plasticity,
                       category, raw_text, winning_axis=None, axis_magnitude=None,
                       contradiction_info=None, forced_focus=None):
        s_state = self.somatic.current_state()
        m_state = self.mental.current_state()

        # Df and Cf are (cx, cy) — final impact
        dfx, dfy = Df
        cfx, cfy = Cf
        d1x, d1y = D1
        c1x, c1y = C1

        s_dist = math.sqrt(dfx**2 + dfy**2)
        m_dist = math.sqrt(cfx**2 + cfy**2)

        dominant = "somatic" if s_dist >= m_dist else "mental"

        # Muscle tone — X-axis dominance drives tension/relaxation
        from layers.muscle_tone import apply_muscle_tone
        muscle_tone = apply_muscle_tone(dfx, s_dist, cfx, m_dist)

        # Scalar display — distance with sign of cy
        Df_display = math.copysign(s_dist, dfy)
        Cf_display = math.copysign(m_dist, cfy)
        D1_display = math.copysign(math.sqrt(d1x**2 + d1y**2), d1y)
        C1_display = math.copysign(math.sqrt(c1x**2 + c1y**2), c1y)

        # Verbal output — two independent channels (somatic/mental
        # descriptors, unrelated to the 16-mode response below — kept
        # as the last-resort fallback if select_axis_response() somehow
        # returns nothing)
        from output.output_layer import get_verbal_somatic, get_verbal_mental
        verbal_s = get_verbal_somatic(s_state, s_dist, chemical_levels=self.chemicals.levels)
        verbal_m = get_verbal_mental(m_state, m_dist)

        # ── RESPONSE — 16-cell matrix + construction matcher ───────────
        # Moved ahead of IDENTITY below so identity/personal-
        # info sharing can be gated on the mode this cycle ACTUALLY
        # landed on (see that section for why) instead of a separate,
        # newly-invented condition -- category/dominant/s_state/m_state
        # are already computed earlier in process, so nothing here
        # depended on running after identity in the first place; the
        # ordering was just incidental.
        from core.response_matrix import dominant_axis, select_axis_response
        if dominant == "somatic":
            axis = dominant_axis(s_state, SOMATIC_KEYS)
        else:
            axis = dominant_axis(m_state, MENTAL_KEYS)

        response = select_axis_response(
            axis, category,
            character_name=self.character_name,
            raw_text=raw_text,
            forced_focus=forced_focus,
            extra_known_names={self.user_name} if getattr(self, "user_name", None) else None,
            # profile (gains) and moment (state) of the engine that speaks,
            # to choose between the mode's variants (core/response_bank.py)
            profile_gains=(self.chemicals.gains if dominant == "somatic"
                           else self.mental_states.mental_gains),
            engine_state=(s_state if dominant == "somatic" else m_state),
            variant_memory=self._variant_memory,
        )

        # Emotion label — word lookup ( worried/valiant review
        # + a second fix found immediately after testing THAT one: "Look,
        # Delia, a monster!" produced text from `investigate` but an
        # emotion word of "tense", which is `suppress`'s ladder, not
        # `investigate`'s -- a self-contradictory line, not a tone nit.
        # Root cause: this used to read `winning_axis` from
        # release_from_axis_push(vec_s) in process -- the axis implied
        # by THIS SINGLE CYCLE's raw incoming push, taken alone -- while
        # the TEXT above reads `axis` from dominant_axis(current_state)
        # -- the axis implied by the character's actual CUMULATIVE state
        # (current push blended with base state, memory, decay, prior
        # cycles). Those are two different questions with two different
        # answers whenever the raw push and the standing state disagree,
        # which is often -- so the word and the sentence could describe
        # two different modes. Now uses the exact same `axis` (and the
        # exact same magnitude, s_dist/m_dist, already computed above for
        # `dominant` itself) that just decided the text: one decision,
        # not two computed from different signals that happen to share a
        # variable name. `winning_axis`/`axis_magnitude` (the
        # release_from_axis_push return values) are no longer read
        # here at all -- release_from_axis_push itself still has to
        # run every cycle regardless (it's what actually releases the
        # chemical into self.chemicals.levels, feeding next cycle's decay
        # -- a real side effect, not just a label lookup), its RETURN
        # value just isn't the right source for this specific word.
        from systems.chemical_system import get_emotion_label
        # get_emotion_label()/MATRIX_MODES key on the bare somatic-style
        # letter ("V","I","Gv","Lv"), not the combined "V/P"-style label
        # `axis` holds (dominant_axis() always returns the combined form,
        # see its own docstring) -- same convention winning_axis used to
        # come in as. Combined label's first half IS that letter by
        # construction (AXIS_TO_CATEGORY's own keys: "Gv/Rr" -> "Gv").
        _emotion_axis = axis.split("/")[0]
        _axis_dist = s_dist if dominant == "somatic" else m_dist
        _quadrant_positive = (dfy >= 0) if dominant == "somatic" else (cfy >= 0)
        emotion_label = get_emotion_label(
            category, _emotion_axis, _axis_dist,
            quadrant_positive=_quadrant_positive,
        )

        # ── IDENTITY — checked before the 16-cell matrix ────────────────
        # BUG FIX (found 2026-09-0X while testing memory/identity recall):
        # output/phrase_builder.py:build_phrase is the ONLY code that
        # answers identity questions ("what's your name?" -> "I am
        # <name>") using the character's injected core_identity_rules
        # (character/injector.py -> motors/core_identity.py CORE_RULES).
        # It used to run first (see output/output_layer.py:generate_output,
        # comment "# Identity first"), but the session wired
        # select_axis_response as the live verbal source and never
        # ported that priority over -- identity questions silently fell
        # through to the construction matcher instead, which has no
        # concept of "identity" at all and produced nonsense (confirmed:
        # asking an injected "Delia" character her name returned "They/It
        # ignore name." instead of "I am Delia", even though
        # build_phrase called directly on the same state already
        # returned the right answer -- the identity DATA and its
        # memory-tier lookup were never broken, only the wiring was).
        # Kept as a short-circuit ahead of the matrix, matching the
        # original priority, rather than folded into RESPONSE_MATRIX --
        # identity recall isn't a category/axis cell, it's a direct
        # lookup against CORE_RULES.
        from output.phrase_builder import build_phrase, build_contradiction_phrase
        identity_phrase = build_phrase(self._last_concepts, core_active, m_dist,
                                        current_mode=response["verb"]) if self._last_concepts else None

        # Identity only pre-empts the matrix in a calm/neutral state.
        # BUG FIX 2 (found right after the first fix, same test): giving
        # identity_phrase unconditional priority was too blunt -- it also
        # overrode genuinely distressed reactions. Confirmed: "a
        # dangerous ghost threatens you and demands your name" resolved
        # underneath to valence="negative" on both engines (fear/anguish
        # tags, chemicals attack/flee/suppress active) and the matrix
        # correctly wanted "I won't just stand here -- I suppress
        # ghost.", but identity_phrase blindly replaced it with a calm
        # "I am Delia" -- a threatened host shouldn't pause to give a
        # polite introduction. Gate on the dominant engine's own already-
        # computed emotional valence (get_somatic_state/get_emotion,
        # same read used for the "emotion" field below) -- BUT valence
        # alone isn't enough either (found immediately after, same test
        # round): a bare, otherwise-neutral "what is your name" sits in
        # an "absent"/"inviable" quadrant purely by sign at near-zero
        # distance (dist~2, i.e. baseline noise), and emotion_mapper
        # labels that "negative" too regardless of magnitude -- so
        # valence-only made even the calm case fall through to the
        # matrix. Require BOTH negative valence AND a real distance
        # (>=10, the same BASELINE_THRESHOLD systems/memory_system.py
        # already uses to tell a real event apart from resting jitter)
        # before letting the matrix override identity.
        _dominant_valence = (
            get_somatic_state(dfx, dfy, chemical_levels=self.chemicals.levels)["valence"]
            if dominant == "somatic" else
            get_emotion(cfx, cfy, mental_state_levels=self.mental_states.levels)["valence"]
        )
        _dominant_dist = s_dist if dominant == "somatic" else m_dist
        _host_distressed = _dominant_valence == "negative" and _dominant_dist >= 10.0

        # ── CONTRADICTION DETECTION — same tier as identity ─────────────
        # CONNECTED (was written, matched the CCM paper's own
        # "fish don't fly" example exactly, but never called from
        # anywhere -- same disconnection pattern identity had before the
        # fix above). Checked first against the requirement that it also
        # works with today's migrated concepts (character/valence.py):
        # confirmed core/pre_input.py:detect_contradiction reads
        # subject.related KEYS as "things this subject can legitimately
        # do" -- for a migrated concept, "related" used to be fully
        # REPLACED by the valence group key alone (e.g. "bird" losing its
        # "fly" key), which made detect_contradiction falsely flag "a
        # bird flies" as a contradiction. Fixed at the source instead of
        # here: character/questionnaire.py:_add_valenced_concept now
        # MERGES the valence key into the concept's existing related
        # dict rather than replacing it, so capability keys like "fly"
        # survive migration. Uses the same _host_distressed gate as
        # identity -- correcting a factual claim is a calm/rational act,
        # same reasoning as "a threatened host doesn't pause to be
        # polite" applies here too.
        # CONTRADICTION DETECTION — same tier as identity. Computed
        # early in process now (see fix above); just consumed here.
        contradiction_phrase = build_contradiction_phrase(contradiction_info or {"is_contradiction": False}, m_dist)

        # `response`/`axis` were computed earlier now (see the block
        # ahead of IDENTITY above) so identity/personal-info sharing can
        # be gated on the mode already picked this cycle.
        # MEMORY RECALL ( core/memory_recall.py): "Do you remember the monster?",
        # "...yesterday?", "What do you think about me?" -> re-creates a stored event.
        # Not gated on distress: a scared host still answers what it remembers (the
        # stored feeling is part of the answer). A contradiction still wins.
        from core.memory_recall import build_recall
        recall = build_recall(self, raw_text, self._last_concepts)
        if recall is None and self._last_claim and self._last_claim["kind"] in ("confirm", "unknown"):
            recall = self._last_claim          # "Did you see the monster?" answered from memory
        recall_phrase = recall["phrase"] if recall else None
        # A contradiction with the host's own memory is not silenced by distress
        # (unlike scene/identity contradictions): it is about what the host lived.
        _memory_contradiction = bool(contradiction_phrase) and \
            (contradiction_info or {}).get("contradiction_type") == "memory"

        phrase = recall_phrase or (contradiction_phrase if _memory_contradiction else None) or (
            response["sentence"] if _host_distressed else (contradiction_phrase or identity_phrase or response["sentence"]))

        # ── VITALITY VOICE — extra sentence from hunger/thirst/loneliness ──
        # NEW (layers/vitality_voice.py): appended after
        # whatever `phrase` already resolved to, never replacing it —
        # this is the host's body/mind talking on top of its reaction
        # to the scene, not instead of it. Uses the SAME mode the matrix
        # just picked (response["verb"]) so the same hunger reads
        # differently depending on what's already happening -- fainting
        # under "surrender", pushing through under "attack". Composed
        # hosts (high Gv/Rr) hold back merely-concerning needs; critical
        # ones always break through (see vitality_voice.py docstring).
        from layers.vitality_voice import get_vitality_message
        _vit_status = self.vitality.status()
        needs_status = {**_vit_status.get("somatic", {}), **_vit_status.get("mental", {}),
                         "sanity": _vit_status.get("sanity", {})}
        vitality_message = get_vitality_message(
            response["verb"], needs_status,
            gv_current=s_state.get("Gv"), rr_current=m_state.get("Rr"),
        )

        verbal = phrase if phrase else (verbal_s if dominant == "somatic" else verbal_m)
        if vitality_message:
            verbal = f"{verbal} {vitality_message}"

        # ── MARKED OUTPUT — mirrors the input contract (the system-state notes
        # "in like this, out like this") ─────────────────────────────
        # Fix: the action fragment used to be built from
        # output/output_layer.py's biomechanical step tables
        # ("orient_body_toward_target, project_weight_forward..."), which
        # read nothing like a real action line ("pointing at the
        # monster"). Reworked to a simpler design: reuse the
        # SAME verb+focus the matrix already picked for the dialogue
        # (response["verb"]/response["subject"] -- includes the speaker
        # selector's forced_focus when this turn was addressed at a
        # named speaker rather than narrated as a world event).
        #
        # 2026-09-21: that "simpler design" was ALSO the whole design --
        # every single turn in a given mode produced the exact same
        # gerund of the exact same verb ("suppress" -> always
        # "suppressing {subject}", "accept" -> always "accepting
        # {subject}"), which read as flat and repetitive over a long
        # scene the same way the pre-response_bank dialogue lines did
        # (see that file's header). Now tries core/action_bank.py first
        # -- same per-mode variant bank + personality/state weighting +
        # anti-repetition machinery as core/response_bank.py, just with
        # gestures/synonyms instead of sentences ("accept" can land on
        # "thanking {subject}", "nodding to {subject}", "welcoming
        # {subject}"...; "attack" on "slaying {subject}", "tearing into
        # {subject}"...). Falls back to the old plain-gerund-via-
        # lemminflect construction (with VERB_PREPOSITIONS for the 6
        # verbs that need one -- "cooperating with", "signaling to
        # user") only if the mode has no entry in ACTION_BANK, so
        # nothing can regress to broken output.
        # the "user" speaker is the player: name them in the action line (*accepting Marta*), or "you"
        _action_subject = response['subject']
        if str(_action_subject).lower() == "user":
            _action_subject = self.user_name or "you"

        from core.action_bank import render_action_from_bank
        action_text = render_action_from_bank(
            response["verb"], _action_subject, axis=response.get("axis"),
            gains=(self.chemicals.gains if dominant == "somatic"
                   else self.mental_states.mental_gains),
            state=(s_state if dominant == "somatic" else m_state),
            memory=self._action_variant_memory,
        )
        if not action_text:
            from lemminflect import getInflection
            from core.response_matrix import VERB_PREPOSITIONS
            _verb_ing = getInflection(response["verb"], tag="VBG")
            _verb_ing = _verb_ing[0] if _verb_ing else response["verb"] + "ing"
            _prep = VERB_PREPOSITIONS.get(response["verb"])
            action_text = f"{_verb_ing} {_prep} {_action_subject}" if _prep \
                else f"{_verb_ing} {_action_subject}"
        if recall:
            action_text = recall["action"]
        elif _memory_contradiction and self._last_claim:
            action_text = self._last_claim["action"]

        from core.marker_parser import format_marked_output
        marked_output = format_marked_output(
            emotion=emotion_label, dialogue=verbal, action=action_text,
        )

        return {
            "dominant":    dominant,
            "verbal":      verbal,
            "verbal_s":    verbal_s,
            "verbal_m":    verbal_m,
            "marked_output": marked_output,
            "action_text": action_text,
            "somatic": {
                "state":    s_state,
                "D1":       round(D1_display, 4),
                "Df":       round(Df_display, 4),
                "distance": round(s_dist, 4),
                "sector":   read_somatic_sector(s_state),
                "emotion":  get_somatic_state(dfx, dfy, chemical_levels=self.chemicals.levels),
                "internal": int_s.get("_active", []),
                "_int_s": int_s,
                "muscle_tone": muscle_tone,
            },
            "mental": {
                "state":    m_state,
                "C1":       round(C1_display, 4),
                "Cf":       round(Cf_display, 4),
                "distance": round(m_dist, 4),
                "sector":   read_mental_sector(m_state),
                "emotion":  get_emotion(cfx, cfy, mental_state_levels=self.mental_states.levels),
                "internal": int_m.get("_active", []),
                "evoked":   int_m.get("_evoked", []),
                "processing": _get_processing_mode_info(cfx, m_dist),
            },
            "core_active":   [r[0] for r in core_active],
            "emotion_label": emotion_label,
            "vitality":      self.vitality.status(),
            "core_status":   self.vitality.core_status(),
            "chemicals":     self.chemicals.status(),
            "mental_states": self.mental_states.status(),
            "memory_s":      self.memory_s.summary(),
            "memory_m":      self.memory_m.summary(),
            "concepts":      self._last_concepts,
            "recall":        recall,
            "threat":        getattr(self, "_last_threat", None),
            "_core_rules":   core_active,
            "_chemicals":    self.chemicals.levels,
            "plasticity":    plasticity,
        }
