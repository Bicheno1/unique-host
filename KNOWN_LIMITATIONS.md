# Unique Host v0.1 — Known limitations

Everything below was observed while assembling and testing the project on 2026-09-20
(Python 3.12, Gradio 6.28, spaCy `en_core_web_sm` 3.8). "Measured" means it was run, not guessed.
Nothing here is a crash: the app ran every test turn without errors.

## 1. What input it understands

- **English only.** Other languages produce junk concepts and nonsense replies.
- **Short, simple, roleplay-style messages work best — one idea per message**, e.g.
  `"Scared" Watch out! <<draws a blade>>`. Each message has three boxes (Emotion / Text / Action); the engine's one-line syntax `"emotion" dialogue <<action>>` is still accepted in Text.
- Measured with Delia on the same bandit scene: at ~5 words it focuses on the bandit and reacts;
  at ~15 words the reaction softens; at ~28–36 words the focus lands on the wrong word
  ("accepting the rain", "the band", "the path").
- Even short messages can misfire when spaCy tags a verb as a noun ("the door slams shut" ->
  "Something's off about the slams") or an uncommon word as an adjective ("raven").
- Unrecognised words are ignored. The lexicon has ~9,000 words; ~31% never reach a questionnaire
  question, so they carry no personal reaction.

## 2. Memory (read this before promising "the character remembers")

What was measured, using Delia v3, Joaquin v1 and a test character:

| Part of memory | Works? | Notes |
|---|---|---|
| **Seeded memories** (`core_fear`, `core_comfort`) | Yes | They are stored as nuclear memories at load and are looked up whenever their word appears. |
| **Recall when a word comes back** (`_memory_vector`) | Yes | If the current focus word is in a stored event, that event adds a push to the reaction. |
| **Saving new events during play** | **Does not work for the tested real characters** | An event is saved only when the engine "returns to baseline" (mental < 11, somatic < 22, on the raw state). Those thresholds fit the neutral default character; the real ones rest higher (Delia v3 21/21, Joaquin 26/16 somatic/mental), so events never close (the numbers predate the current metrics; see finding A, with a table of rest levels). In 11+ calm turns after a bandit attack, nothing was stored for Delia or Joaquin. See `MEMORY_VS_PAPER.md`. |
| **Chemical push / rest** | Improved 2026-09-20 | The chemical push kept the somatic engine up (modes re-released by every input, no depletion). A release reserve + saturation block was added (`DEPLETION_ENABLED`, experimental numbers). Joaquin now settles and stores events; Delia and Mirela barely change. The stored events are the most intense inputs, which for them are pleasant calm phrases, not the bandit scene (finding E in `MEMORY_VS_PAPER.md`). |
| **Event selection (inviability / absence)** | Implemented 2026-09-20 | Threat events are chosen by net inviability (I - V) / absence (A - P) of the raw input and close without the engine returning to rest (finding H). Since finding I, 128 danger words (+245 inflections) carry inviability tags and a character's seed no longer replaces them: with Delia, bandit / monster kills / fire / cage / ghost are stored and recalled. A friendlier character (Joaquin) reacts less, by design. Words outside `db/db_danger.py` still have no tags (e.g. "sword" is in, "siege" is not); the list is a first draft. |
| **Idle drift** | Open | With no input the somatic distance drifts up (heart-rate runaway in the resting quadrant, plus chemical/mental drift; finding F). |
| **Opening System** | Changed 2026-09-20 | Maximum plasticity now needs a threat event in progress or closed in the last 15 cycles (`OPENING_REQUIRES_THREAT`); reactions change more slowly than before within a session. |
| **Tier escalation** (short -> medium -> long) | Works since 2026-09-20 | Medium -> long was unreachable (fixed, tested). The same event must recur within 10 cycles to leave short-term, and it needs 3 repeats for medium and 10 for long. |
| **Spontaneous recall** (`evoked`) | **Dormant** | Fires on unmet needs, not on threat as the paper describes; searches long-term memory only, with placeholder word lists that do not include `cage`/`road`. 0 recalls in 60 idle turns. The `evoked` list in the state is never filled (bug). |
| **Memory shown in the text** | **Only when asked** | Since 2026-09-20 the character recalls on request and checks claims against memory (see "Memory recall and claims" below). It never volunteers a memory. |

Why a character still reacts differently later in a session: **plasticity** (each word's valence
drifts by about 0.25 per exposure, because the Opening rule `dist_mental < 30` is almost always
true), not stored memories. In one test, "a cage" after a
cage scene gave a somatic distance of ~49 versus ~10 for a fresh character, with no new event saved.

Also:
- Session export/resume loads without errors, but vitality needs are not restored (TODO in `exporter.py`),
  and I did not verify that a resumed character behaves the same as before.
- **Suggested wording for the launch text (until events close reliably):** "the character's state changes with what happens to
  them" is safe; "remembers what happened to them" is only true for seeded fears/comforts today.

### Memory recall and claims (added 2026-09-20)

`core/memory_recall.py` and `core/memory_claims.py`; 19 tests in `tests/test_memory_recall.py`
and `tests/test_memory_claims.py`. Enter your name in the **"Your name in the roleplay"** box so
memories are tagged with you.

| You say | The character |
|---|---|
| "Do you remember the monster?" | Recreates the stored event with a template: subject, how it felt, when. |
| "Do you remember yesterday?" / "...long ago?" | Picks an event by time (see below). |
| "What do you think about me?" | Averages the events tagged with your name (good / bad / mixed / "I don't know you yet"). |
| "Did you see the monster yesterday?" | Confirms from memory, or "I don't remember the dragon" (never a flat "no"). |
| "You liked the monster." (stored as bad) | **Contradiction**, same channel as the age check: "That's not how it was..." + the stored feeling. |

Limits:
- **It can only recall what is stored.** With the current event-closing problem, real characters
  (Delia, Joaquin) only have their seeded `core_fear` / `core_comfort` memories, so those are what
  they can recall today. Everything else answers "I don't remember".
- **Time is measured in tiers, not in clock time.** "just now/earlier" -> short-term, "yesterday/last
  time" -> medium, "long ago/as a child" -> long-term. If the wanted tier is empty it uses another
  tier and says when it *really* was ("just now"), it never invents a time.
- **Good/bad words come from a closed list** (about 40 each) in `memory_claims.py`, because the
  lexicon's emotional tags are empty for most words. Unknown words only confirm, they never contradict.
  A negation flips the polarity ("didn't hurt you" = good).
- A message counts as a claim only if it is about "you"/"me"/"we", in the past, and not a recall
  question. Present-tense narration is never judged. Roles are not compared ("the monster attacked
  you" and "you attacked the monster" read the same).
- Threat events are negative by construction, so "What do you think about me?" leans negative for a stranger and "my friend, even when things go wrong" for the seeded friend; positive shared moments are not stored (only threat and distance events exist).
- Every event is tagged with whoever is speaking (the named speaker, or your name for Narrator / You), so "What do you think about me?" reflects the character's
  strong reactions while you were present, including reactions to your own questions.
- The contradiction with memory is not silenced by distress (unlike scene/identity contradictions);
  it is still dropped when the mental distance is 90 or more.
- Wording of all recall templates is a first draft for the author to review.

## 3. Reactions and replies

- **Most lexicon words carry no emotional load.** Only ~67 hand-written concepts plus the
  words reached by your questionnaire answers push anything. First impressions can look off:
  a bandit with a drawn blade got "We welcome the bandit. Gladly." for one character.
- **One slider covers many words.** `people_opinion` also drives `bandit`, `villain`, `hero`, so a
  friendly-to-people character welcomes a bandit.
- **Ties between axes fall into "benefit"** (first axis wins). With flat answers every stimulus
  ties, and the character says "accept" to everything. The creator warns about unanswered sections.
- **Bare action messages read flatter than messages with an emotion tag.**
- Contradiction detection is deliberately low-recall: "a cow flies" is not flagged (cow/dog/cat
  resolve to the concept `pet`), and people flying or objects with living verbs are never flagged.
- Identity: only **age** is verified ("You are 40" -> "I am 27 years old"). "How old are you?"
  is not answered (there is no `age` concept). Father/mother/pet answers are gated by the
  character's mode and may be withheld.
- Replies come from a closed phrase bank (84 phrases); wording and `lean` tags are a draft to
  review. `layers/vitality_voice.py` phrases are still placeholders.
- With the default 16 modes, only 3–4 are reached by a flat character (engine, not phrases).
- Ambiguous homonyms (bolt, heart, spike, spell, mark, bark) are decisions left to the author.
- The somatic plateau that never returns to 0 is expected design, not a bug.

- With the "You" speaker the phrase bank puts "you" in a noun slot, so some replies read awkwardly ("You and I handle you side by side"); the action line now names the player (`*accepting Marta*`).

## 4. Character files and the compiler

- **Free-text answers must be one word.** `core_fear` / `core_comfort` / anchors given as phrases
  ("being caged", "the open road") have no effect. In `delia_adventurer_v3.json` Delia's fear is
  "being caged", so `<<locks her in a cage>>` got "That's fair. We say yes to the cage."
  Recompiled with `core_fear="cage"`, the same input made her surrender.
- Use `delia_adventurer_v4.json` and `joaquin_adventurer_v2.json` (see `fullcompiler/characters/README.md`); Delia's chemistry sliders are still at the default.
- **`delia_adventurer_v3.json` (older) is thin:** `identity_anchors` is empty; the body and mind chemistry
  sections (40 sliders) and 87 of 96 likes-tree questions were left at the default 5.
  `delia_answers.json` has none of the four anchor answers (purpose/security/bond/structure).
- Sliders left at 5 mean "neutral", indistinguishable from "answered 5". The creator's warning
  is a heuristic and can false-alarm.
- The tree has ~2,300 words without a question (units, shapes, mixed groups) and 472 proper names
  excluded on purpose.

## 5. Mismatches between the packages

- `fullcompiler/lexicon_db/db_lexicon.py` lacks the 11 sense corrections and 16 new words applied in
  `fullsystem/db/` (blade, club, staff, arrow, crown...). It cannot be replaced by the engine's copy
  because that copy imports `fullsystem`, and the compiler must stay independent. The likes tree may
  still place "blade" under the plant branch.
- The two `db_concepts.py` copies differ in base keys: `how` / `how_question`, `key` / `keys`,
  and the tone concepts (`angry_tone`, `friendly_tone`, `urgent_tone` vs `angry`, `kind`, `urgent`).
  Nothing failed, but the compiler README's "naming contract" is not fully true today.
- A seed node never replaces a base concept of type `language` (father, mother, pet, be, angry,
  urgent). As a result, the questionnaire's valence for `angry` and `urgent` is ignored.
- `core/input_formats.py` and `core/format_selector.py` are unfinished skeletons. The UI no longer
  uses them. Six modules have no importer (see SESSION_STATE §6); archive them only after checking.
- `agent.py --viz` points to a `visualizer` module that does not exist.
- Old characters made before the English rename may add duplicate concepts (`tu`, `donde`...).
  Regenerate them with the compiler.
- Loading a character replaces the previous one; the engine keeps its databases at module level,
  so **two people using one hosted copy at the same time would overwrite each other's character.**
  Fine locally; not safe for a public multi-user deployment.

## 6. Setup and legal

- The spaCy model and NLTK data are separate downloads (see README). Dependencies are unpinned;
  tested only on Python 3.12 and Gradio 6.28 (a Gradio 5 fallback exists but is untested). The UI
  was served and its functions called directly; it was not clicked through in a browser.
- License: PolyForm Noncommercial 1.0.0 (unmodified text) with a `NOTICE`. The attribution terms
  of WordNet and `wordfreq`, which the lexicon was built from, were not reviewed.
- The reporting channel in the README is still a placeholder.
- The interface has a speaker selector (Narrator / You / any name); the default is Narrator. The engine reacts to a named speaker by naming them as the target of its reply; a speaker is not a second host (one host per process).

## 7. Tests

- Existing suites pass: homonyms (6), contradiction (3), response bank (14), memory recall (11), speakers (10), message fields (8), memory claims (9), memory tiers (7), chemical depletion (7), memory threat (11), danger tags (8), compiler (19).
- Not covered by any test: the injector reset, the phrase changes made on 2026-09-20, session
  resume, the UI, and natural event closing during play.
