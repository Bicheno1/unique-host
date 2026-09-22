# systems/memory_system.py — CCM v4
#
# MEMORY ARCHITECTURE
# ═══════════════════
#
# CONTEXT WINDOW — active input being processed right now.
#   Accumulates concepts each cycle. Detects events by curve shape:
#   baseline → peak → return to baseline. Each complete curve = one event.
#   Events are classified by peak height (mental scale 0–200, somatic scale 0–400).
#
# EVENT CLASSIFICATION
#   mental:   0–8 micro  |  8–50 medium  |  50–90 large  |  90+ major
#   somatic:  0–6 micro  |  6–100 medium  |  100–180 large  |  180+ major
#
# EVENT GRAPH — 3 key points (bezier-like curve):
#   start: (D, C) at baseline before event
#   peak:  (D, C) at maximum activation
#   end:   (D, C) after returning toward baseline
#
# SHORT TERM — last N events. Each: event text + graph.
#   Capacity: 10. Age out after 10 cycles with no reinforcement.
#
# MEDIUM TERM — compressed events. Promoted from short term by repetition (3x).
#   Stores reduced concept list + compressed graph.
#   Capacity: 100. Fades after ~100 cycles.
#
# LONG TERM — significant events. Two promotion paths:
#   1. Repetition: medium term event seen 10x.
#   2. High activation: major event that self-regulated back to baseline.
#   Capacity: 100. nuclear events never deleted.
#
# CORE (nuclear) — personality-defining events.
#   System was in critical state AND self-regulated back to near-center.

import math

# ── THRESHOLDS ────────────────────────────────────────────────────────────────
# Euclidean distances to center for event classification
# mental  (vars 0-200): micro<8   medium<50  large<90  major>=170
# somatic (vars 0-400): micro<6   medium<100 large<180 major>=340
# micro lowered to 8/6 to capture soft events (melody, whisper, breeze)

MENTAL_MICRO  = 8     # was 20 — lowered to capture soft events
MENTAL_MEDIUM = 50
MENTAL_LARGE  = 90
MENTAL_MAJOR  = 170

SOMATIC_MICRO  = 6    # was 40 — lowered to capture soft events
SOMATIC_MEDIUM = 100
SOMATIC_LARGE  = 180
SOMATIC_MAJOR  = 340

BASELINE_THRESHOLD     = 11     # real neutral state C~9.2 — closes event when host returns to rest
# ── THREAT EVENTS ( paper /) ─────────────────────────────
# The paper says memories scale by repetition and IMPACT, and that plasticity responds to
# high-INVIABILITY / high-ABSENCE events. Until now an event was any displacement of the engine
# in any direction (distance), so a pleasant input ("birds sing") could outrank a threat, and events
# only closed if the engine came back to rest (which real characters never do, see
# MEMORY_VS_PAPER.md finding A). Now cycle_manager also passes a THREAT signal: the NET inviability
# (I - V) and NET absence (A - P) of the raw input, measured before the state scaling. A threat
# event starts when the normalised signal (somatic /400, mental /200) reaches THREAT_START, and closes
# after THREAT_QUIET_CYCLES consecutive cycles below it, whatever the engine's resting distance is.
# Its valence is negative by definition. THREAT_EVENTS_ENABLED = False restores the old behaviour.
SOMATIC_SCALE = 400.0   # axis ranges the threat signal is normalised by (core/formulas.py)
MENTAL_SCALE  = 200.0
THREAT_EVENTS_ENABLED = True
THREAT_START          = 0.10    # normalised: net inviability >=40 (somatic) or net absence >=20 (mental)
THREAT_QUIET_CYCLES   = 2
THREAT_DEDUPE_WINDOW  = 8       # a distance event that overlaps a threat event closed this recently is dropped

_CLASS_RANK = {None: 0, "micro": 1, "medium": 2, "large": 3, "major": 4}

HIGH_MENTAL_THRESHOLD  = 90     # high mental distance
HIGH_SOMATIC_THRESHOLD = 180    # high somatic distance
NUCLEAR_THRESHOLD      = 10     # near-center threshold to mark nuclear

SHORT_TERM_MAX  = 10
MEDIUM_TERM_MAX = 100
LONG_TERM_MAX   = 100

SHORT_TERM_AGE  = 10
MEDIUM_TERM_AGE = 100

SHORT_TO_MEDIUM_REPS = 3
MEDIUM_TO_LONG_REPS  = 10

EVENT_START_MENTAL  = 10    # was 20 — lowered for soft events (melody, breeze)
EVENT_START_SOMATIC = 8     # was 40

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _mental_dist(s):
    mx = s.get("Er", 0.0) - s.get("Rr", 0.0)
    my = s.get("P",  0.0) - s.get("A",  0.0)
    return math.sqrt(mx**2 + my**2)

def _somatic_dist(s):
    sx = s.get("Lv", 0.0) - s.get("Gv", 0.0)
    sy = s.get("V",  0.0) - s.get("I",  0.0)
    return math.sqrt(sx**2 + sy**2)

def _mental_sign(s):
    """
    Signed, unlike _mental_dist(): raw (Er-Rr, P-A), without
    sqrt. my > 0 -> P dominates over A ("good"/present memory). my < 0
    -> A dominates over P ("bad"/absent memory). This is what
    _mental_dist() throws away by returning only magnitude -- without
    this, memory can't know which way to push when evoked.
    """
    return (s.get("Er", 0.0) - s.get("Rr", 0.0), s.get("P", 0.0) - s.get("A", 0.0))

def _somatic_sign(s):
    """Signed, analogous to _mental_sign() -- (Lv-Gv, V-I)."""
    return (s.get("Lv", 0.0) - s.get("Gv", 0.0), s.get("V", 0.0) - s.get("I", 0.0))

def _event_valence(sign_s, sign_m):
    """'positive' / 'negative' / 'neutral' from the signed peak of an event:
    somatic (Lv-Gv, V-I) and mental (Er-Rr, P-A). V>I and P>A = good/present.
    Somatic raw scale is ~0-400, mental ~0-200, so each is normalised first.
    Used by core/memory_recall.py to say HOW an event felt."""
    v = (sign_s[1] / 400.0) + (sign_m[1] / 200.0)
    if v > 0.05:  return "positive"
    if v < -0.05: return "negative"
    return "neutral"

def _classify(mental_peak, somatic_peak):
    if mental_peak >= MENTAL_MAJOR  or somatic_peak >= SOMATIC_MAJOR:  return "major"
    if mental_peak >= MENTAL_LARGE  or somatic_peak >= SOMATIC_LARGE:  return "large"
    if mental_peak >= MENTAL_MEDIUM or somatic_peak >= SOMATIC_MEDIUM: return "medium"
    if mental_peak >= MENTAL_MICRO  or somatic_peak >= SOMATIC_MICRO:  return "micro"
    return None

def _max_class(a, b):
    return a if _CLASS_RANK[a] >= _CLASS_RANK[b] else b

def _key(concepts, n=5):
    seen = []
    for c in concepts:
        if c not in seen: seen.append(c)
    return seen[:n]

def _compress(concepts, n=3):
    seen = []
    for c in concepts:
        if c not in seen: seen.append(c)
    return seen[:n]

# ── MEMORY SYSTEM ─────────────────────────────────────────────────────────────

class MemorySystem:
    def __init__(self):
        # Context window state
        self._ctx_concepts   = []
        self._ctx_start      = None
        self._ctx_start_sign_s = (0.0, 0.0)
        self._ctx_start_sign_m = (0.0, 0.0)
        self._ctx_peak_D     = 0.0
        self._ctx_peak_C     = 0.0
        self._ctx_peak_sign_s = (0.0, 0.0)
        self._ctx_peak_sign_m = (0.0, 0.0)
        self._ctx_active     = False
        self._ctx_cycle      = 0

        # Threat-event context (separate segmentation, see THREAT EVENTS above)
        self._thr_active   = False
        self._thr_concepts = []
        self._thr_text     = ""
        self._thr_start    = (0.0, 0.0)
        self._thr_peak_s   = 0.0     # raw threat magnitudes (somatic scale / mental scale)
        self._thr_peak_m   = 0.0
        self._thr_peak_D   = 0.0     # engine distances seen while it lasted
        self._thr_peak_C   = 0.0
        self._thr_quiet    = 0
        self._recent_threat = []     # [(closed_at, set(concepts))]

        self.short_term  = []
        self.medium_term = []
        self.long_term   = []
        self._cycle      = 0
        self.ignore_concepts = set()   # concepts that tag every event (the user's name)
        # Event start / close thresholds (defaults = the historical values). Instance attributes so
        # a character (or a calibration experiment) can move them without touching the module.
        self.start_C = EVENT_START_MENTAL
        self.start_D = EVENT_START_SOMATIC
        self.close_C = BASELINE_THRESHOLD
        self.close_D = BASELINE_THRESHOLD * 2

    # ── MAIN UPDATE ───────────────────────────────────────────────────────────

    def update(self, text, concepts, somatic_state, mental_state, threat_s=0.0, threat_m=0.0):
        """threat_s / threat_m: magnitude of this cycle's inviability / absence / danger release
        (0.0 = none). Optional: without them only the distance tracker runs, as before."""
        self._cycle += 1
        D = _somatic_dist(somatic_state)
        C = _mental_dist(mental_state)
        self._age_memories()
        threat_event = None
        if THREAT_EVENTS_ENABLED:
            threat_event = self._track_threat(text, concepts, D, C, threat_s, threat_m)
        event = self._track_curve(text, concepts, D, C, somatic_state, mental_state)
        if event and self._duplicates_recent_threat(event):
            event = None                      # the threat tracker already stored this episode
        if threat_event:
            self._promote(threat_event)
        if event:
            self._promote(event)
        return threat_event or event

    # ── THREAT TRACKING ───────────────────────────────────────────────────────

    def _track_threat(self, text, concepts, D, C, threat_s, threat_m):
        signal = max(threat_s / SOMATIC_SCALE, threat_m / MENTAL_SCALE)
        hot = signal >= THREAT_START
        if not self._thr_active:
            if not hot:
                return None
            self._thr_active   = True
            self._thr_concepts = list(concepts)
            self._thr_text     = text
            self._thr_start    = (round(D, 4), round(C, 4))
            self._thr_peak_s   = threat_s
            self._thr_peak_m   = threat_m
            self._thr_peak_D   = D
            self._thr_peak_C   = C
            self._thr_quiet    = 0
            return None
        self._thr_peak_D = max(self._thr_peak_D, D)
        self._thr_peak_C = max(self._thr_peak_C, C)
        if hot:
            self._thr_quiet = 0
            for c in concepts:
                if c not in self._thr_concepts:
                    self._thr_concepts.append(c)
            self._thr_peak_s = max(self._thr_peak_s, threat_s)
            self._thr_peak_m = max(self._thr_peak_m, threat_m)
            return None
        self._thr_quiet += 1
        if self._thr_quiet < THREAT_QUIET_CYCLES:
            return None
        event = self._close_threat_event(D, C)
        self._reset_threat()
        return event

    def _close_threat_event(self, end_D, end_C):
        # impact = the bigger of what the threat released and how far the engine moved
        peak_C = max(self._thr_peak_m, self._thr_peak_C)
        peak_D = max(self._thr_peak_s, self._thr_peak_D)
        ec = _max_class(_classify(self._thr_peak_m, self._thr_peak_s), _classify(self._thr_peak_C, self._thr_peak_D))
        if not ec:
            return None
        concepts = _key(self._thr_concepts)
        graph = {
            "start": self._thr_start,
            "peak":  (round(peak_D, 4), round(peak_C, 4)),
            "end":   (round(end_D, 4), round(end_C, 4)),
            # inviability / absence by definition: V-I and P-A negative
            "peak_sign_somatic": (0.0, -max(self._thr_peak_s, 1.0)),
            "peak_sign_mental":  (0.0, -max(self._thr_peak_m, 1.0)),
            "end_sign_somatic":  (0.0, 0.0),
            "end_sign_mental":   (0.0, 0.0),
        }
        self._recent_threat.append((self._cycle, set(concepts)))
        self._recent_threat = self._recent_threat[-10:]
        return {
            "text":         self._thr_text,
            "concepts":     concepts,
            "graph":        graph,
            "event_class":  ec,
            "is_nuclear":   False,
            "mental_peak":  round(peak_C, 4),
            "somatic_peak": round(peak_D, 4),
            "age":          0,
            "reps":         1,
            "closed_at":    self._cycle,
            "valence":      "negative",
            "source":       "threat",
        }

    def threat_recently(self, window):
        """True while a threat event is in progress or closed within `window` cycles
        (used by the plasticity Opening System)."""
        if self._thr_active:
            return True
        return any(self._cycle - closed_at <= window for closed_at, _ in self._recent_threat)

    def _reset_threat(self):
        self._thr_active   = False
        self._thr_concepts = []
        self._thr_text     = ""
        self._thr_peak_s = self._thr_peak_m = self._thr_peak_D = self._thr_peak_C = 0.0
        self._thr_quiet    = 0

    def _duplicates_recent_threat(self, event):
        ign = self.ignore_concepts
        cs = set(event.get("concepts", [])) - ign
        for closed_at, concepts in self._recent_threat:
            if self._cycle - closed_at <= THREAT_DEDUPE_WINDOW and cs & (concepts - ign):
                return True
        return False

    # ── CURVE TRACKING ────────────────────────────────────────────────────────

    def _track_curve(self, text, concepts, D, C, somatic_state, mental_state):
        at_baseline = C < self.close_C and D < self.close_D

        if not self._ctx_active:
            if C >= self.start_C or D >= self.start_D:
                self._ctx_active   = True
                self._ctx_concepts = list(concepts)
                self._ctx_start    = (round(D, 4), round(C, 4))
                self._ctx_start_sign_s = _somatic_sign(somatic_state)
                self._ctx_start_sign_m = _mental_sign(mental_state)
                self._ctx_peak_D   = D
                self._ctx_peak_C   = C
                self._ctx_peak_sign_s = _somatic_sign(somatic_state)
                self._ctx_peak_sign_m = _mental_sign(mental_state)
                self._ctx_cycle    = 1
        else:
            self._ctx_cycle += 1
            for c in concepts:
                if c not in self._ctx_concepts:
                    self._ctx_concepts.append(c)
            if D > self._ctx_peak_D:
                self._ctx_peak_D = D
                self._ctx_peak_sign_s = _somatic_sign(somatic_state)
            if C > self._ctx_peak_C:
                self._ctx_peak_C = C
                self._ctx_peak_sign_m = _mental_sign(mental_state)

            if at_baseline and self._ctx_cycle >= 2:
                event = self._close_event(text, D, C, somatic_state, mental_state)
                self._reset_ctx()
                return event
        return None

    def _close_event(self, text, end_D, end_C, somatic_end, mental_end):
        ec = _classify(self._ctx_peak_C, self._ctx_peak_D)
        if not ec:
            return None

        graph = {
            "start": self._ctx_start,
            "peak":  (round(self._ctx_peak_D, 4), round(self._ctx_peak_C, 4)),
            "end":   (round(end_D, 4), round(end_C, 4)),
            # signed -- (Lv-Gv, V-I) / (Er-Rr, P-A) at each point. Without
            # this, evoke() can say HOW MUCH a memory hit but not
            # WHICH WAY (good/present vs bad/absent) -- see
            # _memory_vector() in core/pre_input.py, which today assumes
            # always "bad" for lack of this data.
            "peak_sign_somatic": self._ctx_peak_sign_s,
            "peak_sign_mental":  self._ctx_peak_sign_m,
            "end_sign_somatic":  _somatic_sign(somatic_end),
            "end_sign_mental":   _mental_sign(mental_end),
        }

        is_nuclear = (
            (self._ctx_peak_C >= HIGH_MENTAL_THRESHOLD or
             self._ctx_peak_D >= HIGH_SOMATIC_THRESHOLD) and
            end_D < BASELINE_THRESHOLD * 2 and
            end_C < NUCLEAR_THRESHOLD
        )

        return {
            "text":         text,
            "concepts":     _key(self._ctx_concepts),
            "graph":        graph,
            "event_class":  ec,
            "is_nuclear":   is_nuclear,
            "mental_peak":  round(self._ctx_peak_C, 4),
            "somatic_peak": round(self._ctx_peak_D, 4),
            "age":          0,
            "reps":         1,
            #  (memory recall): when it closed (in cycles) and how it felt.
            "closed_at":    self._cycle,
            "valence":      _event_valence(self._ctx_peak_sign_s, self._ctx_peak_sign_m),
        }

    def _reset_ctx(self):
        self._ctx_concepts = []
        self._ctx_start    = None
        self._ctx_start_sign_s = (0.0, 0.0)
        self._ctx_start_sign_m = (0.0, 0.0)
        self._ctx_peak_D   = 0.0
        self._ctx_peak_C   = 0.0
        self._ctx_peak_sign_s = (0.0, 0.0)
        self._ctx_peak_sign_m = (0.0, 0.0)
        self._ctx_active   = False
        self._ctx_cycle    = 0

    # ── PROMOTION ─────────────────────────────────────────────────────────────

    def _promote(self, event):
        if not event:
            return
        if event["is_nuclear"] or event["event_class"] == "major":
            self._add_long(event)
            return

        existing_s = self._find(self.short_term, event["concepts"])
        if existing_s:
            existing_s["reps"] += 1
            existing_s["age"]   = 0
            # Fix: escalation medium -> long was unreachable. Repetitions were only
            # counted on the SHORT entry, so the medium entry stayed at reps=3 forever (never
            # reaching MEDIUM_TO_LONG_REPS) and its age was never reset. Now a repeat
            # reinforces whichever higher tier already holds this event.
            existing_l = self._find(self.long_term, existing_s["concepts"])
            if existing_l:                                   # already long-term: just reinforce
                existing_l["reps"] = existing_l.get("reps", 1) + 1
                return
            if existing_s["reps"] >= SHORT_TO_MEDIUM_REPS:
                self._add_medium(existing_s)
                existing_m = self._find(self.medium_term, existing_s["concepts"])
                if existing_m:
                    existing_m["reps"] = max(existing_m["reps"], existing_s["reps"])
                    existing_m["age"]  = 0
                    if existing_m["reps"] >= MEDIUM_TO_LONG_REPS:
                        self._add_long(existing_m)
                        self.medium_term.remove(existing_m)   # long supersedes medium
            return

        self._add_short(event)

        if event["event_class"] == "large":
            existing_m = self._find(self.medium_term, event["concepts"])
            if existing_m:
                existing_m["reps"] += 1
                existing_m["age"]   = 0
                if existing_m["reps"] >= MEDIUM_TO_LONG_REPS:
                    self._add_long(existing_m)

    def _find(self, memory_list, concepts):
        # `ignore_concepts` (the user's name, set by cycle_manager_v5) tags EVERY event;
        # it must not make two different events look like the same one.
        ign = self.ignore_concepts
        cs = set(concepts) - ign
        for entry in memory_list:
            overlap = cs & (set(entry.get("concepts", [])) - ign)
            if overlap and len(overlap) >= max(1, len(cs) // 2):
                return entry
        return None

    def _add_short(self, event):
        self.short_term.append({
            "text":         event["text"],
            "concepts":     _key(event["concepts"]),
            "graph":        event["graph"],
            "event_class":  event["event_class"],
            "is_nuclear":   event["is_nuclear"],
            "mental_peak":  event["mental_peak"],
            "somatic_peak": event["somatic_peak"],
            "closed_at":    event.get("closed_at"),
            "valence":      event.get("valence"),
            "source":       event.get("source", "distance"),
            "age": 0, "reps": 1,
        })
        if len(self.short_term) > SHORT_TERM_MAX:
            non = [e for e in self.short_term if not e["is_nuclear"]]
            nuc = [e for e in self.short_term if e["is_nuclear"]]
            self.short_term = nuc + non[-(SHORT_TERM_MAX - len(nuc)):]

    def _add_medium(self, event):
        entry = {
            "concepts":     _compress(event["concepts"]),
            "graph":        event["graph"],
            "event_class":  event["event_class"],
            "is_nuclear":   event["is_nuclear"],
            "mental_peak":  event["mental_peak"],
            "somatic_peak": event["somatic_peak"],
            "closed_at":    event.get("closed_at"),
            "valence":      event.get("valence"),
            "source":       event.get("source", "distance"),
            "age": 0, "reps": event.get("reps", 1),
        }
        if not self._find(self.medium_term, entry["concepts"]):
            self.medium_term.append(entry)
        if len(self.medium_term) > MEDIUM_TERM_MAX:
            non = [e for e in self.medium_term if not e["is_nuclear"]]
            nuc = [e for e in self.medium_term if e["is_nuclear"]]
            self.medium_term = nuc + non[-(MEDIUM_TERM_MAX - len(nuc)):]

    def _add_long(self, event):
        entry = {
            "concepts":     _compress(event["concepts"], n=4),
            "graph":        event["graph"],
            "event_class":  event["event_class"],
            "is_nuclear":   event["is_nuclear"],
            "mental_peak":  event["mental_peak"],
            "somatic_peak": event["somatic_peak"],
            "closed_at":    event.get("closed_at"),
            "valence":      event.get("valence"),
            "source":       event.get("source", "distance"),
            "reps":         event.get("reps", 1),
        }
        self.long_term.append(entry)
        if len(self.long_term) > LONG_TERM_MAX:
            non = [e for e in self.long_term if not e["is_nuclear"]]
            nuc = [e for e in self.long_term if e["is_nuclear"]]
            self.long_term = nuc + non[-(LONG_TERM_MAX - len(nuc)):]

    # ── AGING ─────────────────────────────────────────────────────────────────

    def _age_memories(self):
        for e in self.short_term:  e["age"] += 1
        for e in self.medium_term: e["age"] += 1
        self.short_term  = [e for e in self.short_term  if e["is_nuclear"] or e["age"] < SHORT_TERM_AGE]
        self.medium_term = [e for e in self.medium_term if e["is_nuclear"] or e["age"] < MEDIUM_TERM_AGE]

    # ── EVOCATION ─────────────────────────────────────────────────────────────

    def evoke(self, current_concepts, current_distance):
        if not self.long_term:
            return []
        evoked = []
        cs = set(current_concepts)
        for event in self.long_term:
            if not (cs & set(event.get("concepts", []))):
                continue
            pD, pC = event["graph"]["peak"]
            peak_dist = math.sqrt(pD**2 + pC**2)
            # relative threshold: 40% of peak distance, minimum 5
            threshold = max(5.0, peak_dist * 0.40)
            if abs(peak_dist - current_distance) <= threshold:
                evoked.append(event)
        return evoked

    # ── STATUS ────────────────────────────────────────────────────────────────

    def context_status(self):
        return {
            "active":   self._ctx_active,
            "concepts": self._ctx_concepts,
            "start":    self._ctx_start,
            "peak":     (round(self._ctx_peak_D, 4), round(self._ctx_peak_C, 4)),
            "cycle":    self._ctx_cycle,
        }

    def summary(self):
        nuc = [e for e in self.long_term if e["is_nuclear"]]
        return {
            "context_active":   self._ctx_active,
            "short_term_size":  len(self.short_term),
            "short_term_last":  self.short_term[-3:] if self.short_term else [],
            "medium_term_size": len(self.medium_term),
            "long_term_total":  len(self.long_term),
            "nuclear_total":    len(nuc),
        }

    def get_context(self):
        return {
            "context_window": self.context_status(),
            "short_term":     self.short_term,
            "medium_term":    self.medium_term,
            "long_term":      self.long_term,
        }

    # ── LEGACY STUBS ──────────────────────────────────────────────────────────

    def update_short_term(self, text): pass
    def update_medium_term(self, concepts): pass
    def track_state(self, distance, concepts, somatic_state, mental_state): pass
    def try_record_long_term(self, current_distance, somatic_state, mental_state, concepts): return None
