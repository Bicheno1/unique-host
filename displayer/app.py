# app.py — UNIQUE HOST (Gradio interface)
#
# TAB 1 — Character Creator: questionnaire -> character.json
#          (+ a "looks incomplete" report before you use it)
# TAB 2 — Load & Chat: load character.json -> roleplay chat
#          -> export / resume a session snapshot
#
# This file has NO engine or questionnaire logic of its own. It only calls
# `fullcompiler` (Tab 1) and `fullsystem` (Tab 2).
#
# Messages: three boxes (Emotion / Text / Action). The engine's own syntax, used on its output and
# still accepted in the Text box, is:
#     "emotion" dialogue <<action>>
#     e.g.  "Angry" Get out of here <<slams the door>>

import json
import os
import re
import sys
import tempfile

# ── UNIQUE HOST is split into 3 sibling packages:
#      displayer/   (this folder, the Gradio interface)
#      fullcompiler/  (questionnaire -> character.json)
#      fullsystem/     (CCM engine + databases + json loader)
#    All 3 must live side by side for these imports to work.
_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_BASE, "..", "fullcompiler"))
sys.path.insert(0, os.path.join(_BASE, "..", "fullsystem"))

import gradio as gr

from questionnaire.questionnaire import QUESTIONS, build_character_json
from questionnaire.completeness import check_completeness, format_report
from character.injector import inject_character
from character.exporter import export_session, load_session
from core.marker_parser import parse_marked_input

# The engine understands English only (spaCy en_core_web_sm + English lexicon).
WIP_NOTICE = (
    "**⚠️ Work in progress.** Unique Host is an early experimental release and "
    "may have bugs. It is maintained solely by Akimsa, so fixes may take time. "
    "**English only**, and it works best with **short, simple, roleplay-style messages** "
    "(one idea per message). "
    "Try it, break it, and report what you find (see the README for where)."
)

_OUT_DIR = tempfile.mkdtemp(prefix="unique_host_")


def warm_up():
    """Loads the spaCy model once at start-up (the engine loads it lazily on the first message,
    which otherwise makes the first reply of a session slow: ~0.4 s warm, several seconds cold)."""
    from core.construction_matcher import get_nlp
    get_nlp()("warm up")


def _path_of(file_obj):
    """gr.File gives a plain path (str) in Gradio 4+, a tempfile-like in older versions."""
    return getattr(file_obj, "name", file_obj)


# ─────────────────────────────────────────────────────────────
# TAB 1 — CHARACTER CREATOR
# ─────────────────────────────────────────────────────────────

def _make_component(key, label, qtype, extra):
    if qtype == "number":
        return gr.Number(label=label, value=extra.get("value"),
                         minimum=extra.get("minimum"), maximum=extra.get("maximum"))
    if qtype == "slider":
        return gr.Slider(label=label,
                         minimum=extra.get("minimum", 1),
                         maximum=extra.get("maximum", 10),
                         value=extra.get("value", 5), step=1)
    return gr.Textbox(label=label)


def _build_questionnaire_inputs():
    """
    Builds one Gradio component per entry of QUESTIONS, returned IN THE SAME
    ORDER as QUESTIONS (generate_character() zips them together). The likes-tree
    questions are contiguous at the end, so they go inside a collapsed
    accordion without changing that order.
    """
    main = [q for q in QUESTIONS if not q[0].startswith("tree__")]
    tree = [q for q in QUESTIONS if q[0].startswith("tree__")]
    assert main + tree == list(QUESTIONS), "tree questions must be contiguous at the end"

    components = [_make_component(*q) for q in main]
    with gr.Accordion(f"Likes tree ({len(tree)} questions) — 1 = dislike, 10 = attraction",
                      open=False):
        components += [_make_component(*q) for q in tree]
    return components


def generate_character(*values):
    answers = {q[0]: v for q, v in zip(QUESTIONS, values)}
    report = format_report(check_completeness(answers))
    character_data = build_character_json(answers)

    name = str(character_data.get("identity", {}).get("name") or "character")
    safe = "".join(c for c in name if c.isalnum() or c in "-_") or "character"
    out_path = os.path.join(_OUT_DIR, f"{safe}_character.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(character_data, f, indent=2, ensure_ascii=False)

    # The full JSON is thousands of lines (one concept per lexicon word);
    # showing only the head keeps the browser responsive.
    preview_lines = json.dumps(character_data, indent=2, ensure_ascii=False).splitlines()
    preview = "\n".join(preview_lines[:120])
    if len(preview_lines) > 120:
        preview += f"\n... ({len(preview_lines) - 120} more lines — use the Save button for the full file)"
    # Third output is the "Save character.json" DownloadButton: it starts disabled and is
    # enabled here, pointing at the freshly written file.
    return report, preview, gr.DownloadButton(value=out_path, interactive=True)


# ─────────────────────────────────────────────────────────────
# TAB 2 — LOAD & CHAT
# ─────────────────────────────────────────────────────────────

def load_character_file(file_obj):
    if file_obj is None:
        return None, "No file uploaded.", []
    try:
        with open(_path_of(file_obj), "r", encoding="utf-8") as f:
            character_data = json.load(f)
        ccm, identity = inject_character(character_data)
    except Exception as e:  # bad JSON, wrong file, old schema...
        return None, f"Could not load that file: {type(e).__name__}: {e}", []
    return ccm, f"Loaded character: {identity.get('name', 'Unnamed')}", []


def load_session_file(ccm, file_obj):
    if ccm is None:
        return ccm, "Load a character first."
    if file_obj is None:
        return ccm, "No session file uploaded."
    try:
        with open(_path_of(file_obj), "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        ccm = load_session(ccm, snapshot)
    except Exception as e:
        return ccm, f"Could not load that session: {type(e).__name__}: {e}"
    return ccm, "Session snapshot loaded."


def export_session_file(ccm):
    if ccm is None:
        return None, "No active character to export."
    out_path = os.path.join(_OUT_DIR, "session_snapshot.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export_session(ccm), f, indent=2, ensure_ascii=False)
    return out_path, "Session exported."


# WHO IS SPEAKING — the engine's "who's talking" selector (CycleManagerV5.process(speaker=...)).
#   "narrator" : the message describes the WORLD ("a bandit blocks the road"); the host reacts to what
#                the sentence says.
#   "user"     : you, the person playing, talk to the host directly.
#   any name   : "Joaquin", "Mark", "bandit" ... an open, growing list. The host reacts to THAT person
#                ("They can't hold the bandit back anymore"), and the memory tags the event with that
#                name, so "What do you think about me?" is about whoever is speaking now.
SPEAKER_NARRATOR = "Narrator"
SPEAKER_YOU = "You"
_INLINE_KNOWN = re.compile(r"^\s*([A-Za-z][A-Za-z' -]{0,24}?)\s*:\s+(\S.*)$", re.S)
_INLINE_NEW = re.compile(r"^\s*@([A-Za-z][A-Za-z' -]{0,24}?)\s*:\s+(\S.*)$", re.S)


def engine_speaker(label):
    """Dropdown label -> value for process(speaker=...)."""
    name = (label or "").strip()
    if not name or name.lower() in ("narrator", "narrator (world)"):
        return "narrator"
    if name.lower() in ("you", "user", "you (user)"):
        return "user"
    return name


def split_speaker_prefix(message, known):
    """Inline switch: "Joaquin: Watch out!" (a known speaker) or "@Marta: Hello" (introduces a new one).
    Returns (speaker_label, text) or (None, message)."""
    m = _INLINE_NEW.match(message or "")
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = _INLINE_KNOWN.match(message or "")
    if m:
        names = {SPEAKER_NARRATOR.lower(): SPEAKER_NARRATOR, SPEAKER_YOU.lower(): SPEAKER_YOU, "user": SPEAKER_YOU}
        names.update({k.lower(): k for k in (known or [])})
        hit = names.get(m.group(1).strip().lower())
        if hit:
            return hit, m.group(2).strip()
    return None, message


def compose_marked(emotion="", dialogue="", action=""):
    """The three separate boxes -> the engine's {"emotion", "dialogue", "action"} dict (no <<>> or quotes
    needed). Backwards compatible: if only the Dialogue box is filled and it contains the old single-line
    syntax (`"Angry" Get out <<slams the door>>`), it is parsed as before."""
    emotion, dialogue, action = (emotion or "").strip(), (dialogue or "").strip(), (action or "").strip()
    if dialogue and not emotion and not action and ("<<" in dialogue or '"' in dialogue):
        return parse_marked_input(dialogue)
    return {"emotion": emotion or None, "dialogue": dialogue or None, "action": action or None}


def format_turn(name, marked):
    """Chat bubble for one turn: **Name** _(emotion)_: dialogue *action*"""
    if not marked or not any(marked.get(k) for k in ("emotion", "dialogue", "action")):
        return ""
    head = f"**{name}**" + (f" _({marked['emotion']})_" if marked.get("emotion") else "")
    body = " ".join(x for x in (marked.get("dialogue"), f"*{marked['action']}*" if marked.get("action") else None) if x)
    return f"{head}: {body}"


def reply_for(ccm, message, speaker="narrator"):
    """
    One chat turn from a marked-syntax string. The engine's own output is `state["marked_output"]`,
    built by CycleManagerV5 from the identity check, the contradiction check, the phrase bank and the
    action text. (The old `build_response()` in core/response_matrix.py is legacy and bypasses all of that.)
    """
    return reply_for_marked(ccm, parse_marked_input(message), speaker)


def reply_for_marked(ccm, marked, speaker="narrator"):
    state = ccm.process(text="", marked_input=marked, speaker=speaker)
    return state.get("marked_output") or "..."


def _speaker_name(engine_speaker_value, user_name):
    if engine_speaker_value == "narrator":
        return SPEAKER_NARRATOR
    if engine_speaker_value == "user":
        return (user_name or SPEAKER_YOU).strip()
    return engine_speaker_value


def chat_turn(ccm, marked, history, user_name="", speaker="narrator"):
    """Runs one turn from an already composed `marked` dict. Returns (history, ccm)."""
    history = history or []
    if not marked or not any(marked.get(k) for k in ("emotion", "dialogue", "action")):
        return history, ccm
    who = speaker or "narrator"
    if ccm is None:
        reply_text = "(No character loaded — go to the Load & Chat tab and load a character.json first.)"
        reply = reply_text
    else:
        try:
            # who YOU are in the roleplay: memories get tagged with it, so the character can
            # answer "What do you think about me?" and "Did I scare you?"
            ccm.user_name = (user_name or "").strip() or None
            reply = reply_for_marked(ccm, marked, who)
        except Exception as e:
            reply = f"(The engine hit an error: {type(e).__name__}: {e}. Please report this.)"
    host = (getattr(ccm, "character_name", None) or "Host") if ccm is not None else "Host"
    parsed = parse_marked_input(reply)
    shown_reply = format_turn(host, parsed) if parsed.get("dialogue") or parsed.get("emotion") or parsed.get("action") else reply
    history = history + [{"role": "user", "content": format_turn(_speaker_name(who, user_name), marked)},
                         {"role": "assistant", "content": shown_reply}]
    return history, ccm


def chat_step(ccm, message, history, user_name="", speaker="narrator"):
    """String version (marked syntax). `speaker` is the engine value ("narrator", "user" or a name).
    Returns (history, ccm, "")."""
    history, ccm = chat_turn(ccm, compose_marked("", message, ""), history, user_name, speaker)
    return history, ccm, ""


def chat_step_fields(ccm, emotion, dialogue, action, history, user_name, speaker_label, speakers):
    """Gradio handler for the three boxes (Emotion / Text / Action): applies an inline "Name: text" or
    "@Name: text" switch written in the Text box, grows the speaker list, and keeps the chosen speaker
    selected for the next message. Returns (history, ccm, emotion, dialogue, action, dropdown, speakers)."""
    speakers = list(speakers or [])
    label = (speaker_label or SPEAKER_NARRATOR).strip() or SPEAKER_NARRATOR
    inline, text = split_speaker_prefix(dialogue, speakers)
    if inline:
        label, dialogue = inline, text
    engine = engine_speaker(label)
    if engine not in ("narrator", "user") and label not in speakers:
        speakers.append(label)
    marked = compose_marked(emotion, dialogue, action)
    empty = not any(marked.get(k) for k in ("emotion", "dialogue", "action"))
    history, ccm = chat_turn(ccm, marked, history, user_name, engine)
    choices = [SPEAKER_NARRATOR, SPEAKER_YOU] + speakers
    if empty:                                      # nothing to send: keep what was typed
        return history, ccm, emotion, dialogue, action, gr.update(choices=choices, value=label), speakers
    return history, ccm, "", "", "", gr.update(choices=choices, value=label), speakers


def chat_step_ui(ccm, message, history, user_name, speaker_label, speakers):
    """One-line version (marked syntax in a single string), kept for scripts and tests.
    Returns (history, ccm, "", dropdown, speakers)."""
    history, ccm, _, _, _, dd, speakers = chat_step_fields(ccm, "", message, "", history, user_name, speaker_label, speakers)
    return history, ccm, "", dd, speakers


# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────

def _chatbot():
    # Gradio 6 only knows the "messages" format; Gradio 4/5 need it requested.
    try:
        return gr.Chatbot(label="UNIQUE HOST", type="messages")
    except TypeError:
        return gr.Chatbot(label="UNIQUE HOST")


def _preview_code():
    # The preview is truncated (first ~120 lines), so the component's own "download" icon would
    # save an incomplete, invalid JSON. Keep only "copy" there; the Save button gives the full file.
    kwargs = dict(label="character.json preview (first lines only)", language="json")
    try:
        return gr.Code(buttons=["copy"], **kwargs)      # Gradio 6
    except TypeError:
        return gr.Code(**kwargs)                        # Gradio 4/5 has no `buttons` argument


def build_demo():
    with gr.Blocks(title="UNIQUE HOST") as demo:
        gr.Markdown("# UNIQUE HOST — a roleplay character that remembers")
        gr.Markdown(WIP_NOTICE)

        with gr.Tab("1. Character Creator"):
            gr.Markdown(
                "Answer the questionnaire, then generate a `character.json`. "
                "Download it and load it in the **Load & Chat** tab. "
                "Sliders you leave at 5 count as *neutral* — the more you answer, "
                "the more your character reacts as themselves."
            )
            question_inputs = _build_questionnaire_inputs()
            with gr.Row():
                generate_btn = gr.Button("Generate character.json", variant="primary", scale=3)
                # Disabled until a character is generated; generate_character() enables it and
                # points it at the new file. Clicking it downloads the full character.json.
                save_btn = gr.DownloadButton("💾 Save character.json", interactive=False, scale=1)
            completeness = gr.Textbox(label="Check before you play", interactive=False, lines=4)
            json_preview = _preview_code()

            generate_btn.click(fn=generate_character, inputs=question_inputs,
                               outputs=[completeness, json_preview, save_btn])

        with gr.Tab("2. Load & Chat"):
            ccm_state = gr.State(None)

            gr.Markdown("### Load a character")
            with gr.Row():
                char_file_input = gr.File(label="character.json")
                load_char_btn = gr.Button("Load character", variant="primary")
            load_status = gr.Textbox(label="Status", interactive=False)

            gr.Markdown("### Resume a previous session (optional)")
            with gr.Row():
                session_file_input = gr.File(label="session_snapshot.json")
                load_session_btn = gr.Button("Load session snapshot")

            gr.Markdown("### Chat")
            user_name_box = gr.Textbox(
                label="Your name in the roleplay (optional)",
                placeholder="e.g. Joaquin — lets the character remember you and answer \"What do you think about me?\"",
            )
            speaker_box = gr.Dropdown(
                label="Who is speaking? (Narrator / You / any name or role)",
                choices=[SPEAKER_NARRATOR, SPEAKER_YOU], value=SPEAKER_NARRATOR, allow_custom_value=True,
            )
            gr.Markdown(
                "**Narrator** describes the world (`a bandit blocks the road`); **You** talks to the host; "
                "type any other name or role (`Joaquin`, `bandit`) and it joins the list. The host reacts to "
                "whoever speaks. Switch inline with `Joaquin: Watch out!` or introduce someone with `@Marta: Hello`."
            )
            speakers_state = gr.State([])
            chatbot = _chatbot()
            with gr.Row():
                emotion_box = gr.Textbox(label="Emotion", placeholder="e.g. Angry, Nervous (optional)", scale=1)
                text_box = gr.Textbox(label="Text (what is said)", placeholder="e.g. Get out of here", scale=3)
                action_box = gr.Textbox(label="Action (what is done)", placeholder="e.g. slams the door (optional)", scale=2)
            send_btn = gr.Button("Send", variant="primary")
            gr.Markdown(
                "Each box is optional but at least one is needed. No `<<>>` or quotes required. "
                "(The old one-line syntax `\"Angry\" Get out <<slams the door>>` still works if you paste it in **Text**.)"
            )

            gr.Markdown("### Export current session")
            export_btn = gr.Button("Export session snapshot")
            export_file = gr.File(label="session_snapshot.json")

            load_char_btn.click(fn=load_character_file, inputs=[char_file_input],
                                outputs=[ccm_state, load_status, chatbot])
            load_session_btn.click(fn=load_session_file, inputs=[ccm_state, session_file_input],
                                   outputs=[ccm_state, load_status])
            chat_inputs = [ccm_state, emotion_box, text_box, action_box, chatbot, user_name_box, speaker_box, speakers_state]
            chat_outputs = [chatbot, ccm_state, emotion_box, text_box, action_box, speaker_box, speakers_state]
            send_btn.click(fn=chat_step_fields, inputs=chat_inputs, outputs=chat_outputs)
            for box in (emotion_box, text_box, action_box):
                box.submit(fn=chat_step_fields, inputs=chat_inputs, outputs=chat_outputs)
            export_btn.click(fn=export_session_file, inputs=[ccm_state],
                             outputs=[export_file, load_status])
    return demo


if __name__ == "__main__":
    warm_up()
    build_demo().launch()
