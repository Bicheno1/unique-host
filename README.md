# Unique Host

> **Work in progress — v0.1.** Early experimental release; expect bugs. English only.

**A real-time character psychology engine — no LLMs, 15ms replies, no GPU, no servers.**
Your NPCs get a mind, a body and a memory that grows with what happens to them.

Create a character, give them a world, and start playing. Your character can remember what happens
during the adventure, keep their identity, experience things, develop their internal state, and use
that history in future interactions. Instead of *"the AI remembers the conversation"*, the goal is
closer to *"the character remembers what happened to them."*

You don't need to build a complicated agent pipeline or configure dozens of systems just to start
roleplaying. **Just create your character and play.**

Unique Host is still an early experimental project, so it has limitations, bugs, and plenty of things
left to improve. That's the point of this release: to let people try it, play with it, and see what
happens.

## 🧬 Built on the Cognitive Coherence Model

Unique Host is a **small, deliberately limited slice** of the Cognitive Coherence Model (CCM) — a
broader cognitive architecture built around two engines, one mental and one somatic, that can agree
or disagree with each other.

In this implementation that means two geometric engines (mental and somatic), a chemistry/state
layer, a memory system, and a 16-mode response matrix. This release keeps the part of the
architecture that matters most for a character you can talk to: a real internal state driving every
reply, tension between what a character says and what it feels, and memory that shapes how future
events are read. Everything else is narrowed down to one domain (roleplay) and one output channel
(text).

It is **not** an LLM: replies come from the engine's state plus a closed bank of phrases. The full
model — other output channels, deliberation across cycles, and the rest of the memory system — is
described in the CCM paper, and it goes well beyond what this first release uses.

## 🎮 What can you do with it?

- **Create a character** by answering a short questionnaire: what they value, what scares them, what comforts them, how they see people and things. Or load one of the two ready characters, **Delia** and **Joaquin**.
- **Play a scene** and watch the same event land differently on different characters. A bandit, a monster or a locked cage doesn't shake everyone the same way.
- **Ask what they remember.** *"Do you remember the monster?"*, *"What do you think about me?"*, *"Did you see the dragon yesterday?"*
- **Try to fool them.** Tell a character something false about the past (*"You liked the monster."*) and see if they check it against what they remember.
- **Prototype an NPC** with a personality and a reaction style, without wiring up a language model.
- **Explore the CCM** in a small, runnable system, if you are curious about cognitive architectures.
- **Run it anywhere.** About 15 ms per reply on a laptop. No GPU, no API, no internet needed after setup.

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

## 💡 Tips

- **Short messages work best.** One idea per message. Long paragraphs can make the character focus on the wrong word.
- **English only** for now.
- In the questionnaire, write fears and comforts as **one word** (`cage`, not `being caged`).
- The more questions you answer, the more your character reacts as themselves.

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
Memory is partial (seeded fears/comforts work and can be recalled on request; new events are not always saved).

- The character reacts through an internal state, keeps its core fear and comfort as permanent memories, and can recall and check things on request.
- Memory of events during play is still being improved and depends on the character.
- Characters don't bring up memories on their own yet. They remember when you ask.

Full list, with measurements: **[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)**.

## 🗺️ What's next

- Better memory of events formed during play, calibrated per character
- A larger vocabulary of danger and emotion words
- Spontaneous recall, so characters bring up memories on their own
- More characters and tools to build a character's world

## Tests

```bash
cd fullsystem     && python tests/test_lexicon_homonyms.py && python tests/test_contradiction.py && python tests/test_response_bank.py && python tests/test_memory_recall.py && python tests/test_memory_claims.py && python tests/test_memory_tiers.py && python tests/test_chemical_depletion.py && python tests/test_memory_threat.py && python tests/test_danger_tags.py && python tests/test_speakers.py && python tests/test_message_fields.py
cd ../fullcompiler && python test_compiler.py
```

## Feedback

Try it, break it, and tell me what you find: open a [GitHub Issue](../../issues) with what you sent and what you expected, or email Akimsa3@proton.me.

## License

[PolyForm Noncommercial 1.0.0](LICENSE). Commercial use requires a separate license: Akimsa3@proton.me

---

### 🌟 Create a character. Start an adventure. See where they go.
