# Unique Host

> **Work in progress — v0.1.** Early experimental release; expect bugs. English only.

**Meet Unique Host!** An experimental system designed specifically for roleplay.
Create a character, give them a world, and start playing.

Your character can remember what happens during the adventure, keep their identity,
experience things, develop their internal state, and use that history in future interactions.
Instead of *"the AI remembers the conversation"*, the goal is closer to
*"the character remembers what happened to them."*

Unique Host is built on the **Cognitive Coherence Model (CCM)**: two geometric engines
(mental and somatic), a chemistry/state layer, a memory system and a 16-mode response matrix.
It is **not** an LLM: replies come from the engine's state plus a closed bank of phrases.

## Quick start

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
python displayer/app.py
```
(or `./setup_and_run.sh` to do it all). Then open the local URL Gradio prints.

0. Two ready characters are in `fullcompiler/characters/` (`delia_adventurer_v4.json`, `joaquin_adventurer_v2.json`).
1. **Character Creator** tab — answer the questionnaire (the "Likes tree" is collapsed; the more you answer, the more your character reacts as themselves) and download `character.json`.
2. **Load & Chat** tab — load it and play. Keep messages short. Each message has three separate boxes,
   all optional (at least one needed): **Emotion** (`Angry`), **Text** (`Get out of here`) and **Action**
   (`slams the door`). No `<<>>` or quotes needed. The host answers in the same three parts, shown as
   **Delia** _(wary)_: I remember the bandit just now. *remembering the bandit*. The engine's one-line syntax
   `"Angry" Get out of here <<slams the door>>` is still accepted if you paste it into **Text**.
3. Choose **who is speaking** with the selector above the chat: **Narrator** describes the world
   (`a bandit steps out of the bushes`), **You** talks to the host, and any other name or role (`Joaquin`, `Mark`,
   `bandit`) joins the list. The host reacts to whoever speaks ("We keep still and watch Mark"), and memories are tagged
   with that name, so `What do you think about me?` is about the current speaker. Switch inline with
   `Joaquin: Watch out!` (known names) or introduce someone with `@Marta: Hello`.
4. Type your name in **"Your name in the roleplay"** so the character remembers *you*. Then you can ask
   `Do you remember the monster?`, `Do you remember yesterday?`, `What do you think about me?`,
   `Did you see the monster?`, or claim something (`You liked the monster.`) and the character checks it against
   what it stored.
5. **Export session snapshot** to resume later.

## What it looks like

A real, unedited run with `fullcompiler/characters/delia_adventurer_v4.json`, playing as Joaquin, in the engine's
one-line syntax (in the app you would type these into the three boxes; wording varies between runs; it is a closed
phrase bank, not a language model):

```
you   > "Calm" Hello Delia. What is your name?
delia > "glad" I am Delia <<accepting the name>>

you   > Who is your father?
delia > "interested" My father is Tomás <<observing the father>>

you   > You are 40 years old, right?
delia > "interested" I am 27 years old <<observing that>>

you   > <<a bandit steps out of the bushes, blade drawn>>
delia > "strained" Breathe. I hold it in and wait for the bandit to move. <<suppressing the bandit>>

you   > "Scared" Watch out Delia, a bandit!
delia > "tense" Steady. Not yet. <<suppressing the bandit>>

you   > <<the bandit lunges at her>>
delia > "tense" I keep still and watch the bandit. Nothing more. <<suppressing the bandit>>

you   > <<the bandit flees into the forest>>
delia > "tense" Breathe. I hold it in and wait for the bandit to move. <<suppressing the bandit>>

you   > <<she sits by the fire and rests>>
delia > "tense" Not yet. I swallow the urge to react to the fire. <<suppressing the fire>>

you   > "Calm" It is quiet again.
delia > "fine" I smile at that and look right past. <<ignoring that>>

you   > Do you remember the bandit?
delia > "wary" I remember the bandit just now, and the steps. It scared me. I can still feel it. <<remembering the bandit>>

you   > You liked the bandit.
delia > "wary" No. That's not what I remember. The bandit just now: I'll never forget how bad that was. <<remembering the bandit>>

you   > Did you see the monster?
delia > "guarded" I don't remember the monster. <<trying to remember the monster>>

you   > <<a monster kills the horse in front of her>>
delia > "guarded" Steady. Not yet. <<suppressing the monster>>

you   > "Panicked" <<blood is everywhere>>
delia > "wary" Move. I flee the blood, now. <<fleeing the blood>>

you   > <<she catches her breath>>
delia > "alert" I think the breath might mean well. Maybe. <<formulating the breath>>

you   > <<a warm breeze>>
delia > "fine" I have other things to think about than the breeze. <<ignoring the breeze>>

you   > Do you remember the monster?
delia > "guarded" The monster just now... yes. It left a bad taste. <<remembering the monster>>

you   > Do you remember the cage?
delia > "wary" I do remember the cage a long time ago. It scared me. I can still feel it. <<remembering the cage>>

you   > What do you think about me?
delia > "wary" Bad things happen around us, but I still count on you. <<thinking about you>>
```

It answers in about 15 ms per message on a laptop, with no GPU and no API. Try the same script with
`joaquin_adventurer_v2.json`: a friendlier character reacts differently to the same scenes.

## Layout

```
displayer/   Gradio interface (no engine logic)
fullcompiler/  questionnaire -> character.json   (independent of the engine)
fullsystem/     CCM engine, databases, character loader, tests
```
The three folders must stay side by side. See each folder's README for details.

## Known limitations (v0.1)

Works best with **short, simple, roleplay-style messages — one idea per message**, in **English only**.
Memory is partial (seeded fears/comforts work and can be recalled on request; new events are not always saved). Full list, with measurements: **[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)**.

## Tests

```bash
cd fullsystem     && python tests/test_lexicon_homonyms.py && python tests/test_contradiction.py && python tests/test_response_bank.py && python tests/test_memory_recall.py && python tests/test_memory_claims.py && python tests/test_memory_tiers.py && python tests/test_chemical_depletion.py && python tests/test_memory_threat.py && python tests/test_danger_tags.py && python tests/test_speakers.py && python tests/test_message_fields.py
cd ../fullcompiler && python test_compiler.py
```

## Feedback

Try it, break it, and tell me what you find: **<ADD REPORTING CHANNEL HERE — GitHub Issues / Discord / form>**

## License

[PolyForm Noncommercial 1.0.0](LICENSE). Commercial use requires a separate license: Akimsa3@proton.me
