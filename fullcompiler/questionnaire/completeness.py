# questionnaire/completeness.py — UNIQUE HOST
#
# check_completeness(answers) -> report dict.  Pure function, no side effects,
# does NOT touch build_character_json().  Meant to be called by the UI right
# before compiling, to warn the user about sections that look skipped.
#
# WHY A HEURISTIC: sliders always carry a value (default 5), so "skipped" and
# "answered 5" arrive identically.  A section is reported as "looks skipped"
# when EVERY slider in it is still at its default (or missing / None / '').
# Someone who genuinely answers 5 to every question in a section gets a
# false alarm — that's why the message says "looks like", never "you skipped".

from questionnaire.questionnaire import (
    QUESTIONS_SECONDARY_IDENTITY, QUESTIONS_PRIMARY_FORTITUDE,
    QUESTIONS_PRIMARY_CHEMISTRY, QUESTIONS_PRIMARY_MENTAL_CHEMISTRY,
    QUESTIONS_TERTIARY_CONCEPTS,
)
from questionnaire.tree_questionnaire import TREE_QUESTIONS, _question_key
from lexicon_db.db_category_words import CATEGORY_WORDS

SLIDER_DEFAULT = 5.0

_SECTIONS = {
    "Fortitude (personality basics)":      QUESTIONS_PRIMARY_FORTITUDE,
    "Body reactions (chemistry)":          QUESTIONS_PRIMARY_CHEMISTRY,
    "Mind reactions (mental chemistry)":   QUESTIONS_PRIMARY_MENTAL_CHEMISTRY,
    "Opinions about the world":            [q for q in QUESTIONS_TERTIARY_CONCEPTS if q[2] == "slider"],
    "Likes tree":                          TREE_QUESTIONS,
}
_FREE_TEXT_SINGLE_WORD = ["core_fear", "core_comfort", "purpose_source",
                          "security_source", "valued_bond", "structure_source"]


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _unanswered(answers, key):
    v = answers.get(key)
    if _blank(v):
        return True
    try:
        return float(v) == SLIDER_DEFAULT
    except (TypeError, ValueError):
        return False


def _tree_words_left_neutral(answers):
    """Words of the likes tree whose EVERY branch is still unanswered."""
    touched, all_words = set(), set()
    for path, words in CATEGORY_WORDS.items():
        all_words.update(words)
        if words and not _unanswered(answers, _question_key(path)):
            touched.update(words)
    return len(all_words - touched), len(all_words)


def check_completeness(answers: dict) -> dict:
    report = {"sections": {}, "warnings": [], "ok": True}

    for name, questions in _SECTIONS.items():
        keys = [q[0] for q in questions]
        missing = [k for k in keys if _unanswered(answers, k)]
        report["sections"][name] = {"total": len(keys), "unanswered": len(missing),
                                    "unanswered_keys": missing}
        if len(missing) == len(keys):
            report["warnings"].append(f"'{name}' looks completely skipped (all {len(keys)} "
                                      f"questions are still at the default). This part of the "
                                      f"character will be flat/neutral.")
        elif name == "Likes tree" and len(missing) > len(keys) // 2:
            neutral, total = _tree_words_left_neutral(answers)
            report["warnings"].append(f"'{name}': {len(missing)} of {len(keys)} questions look "
                                      f"unanswered — about {neutral} of {total} words will have "
                                      f"no personal reaction.")

    if _blank(answers.get("name")) or str(answers.get("name")).strip() == "Unnamed":
        report["warnings"].append("The character has no name.")
    if _blank(answers.get("age")):
        report["warnings"].append("The character has no age.")

    for key in _FREE_TEXT_SINGLE_WORD:
        v = answers.get(key)
        if not _blank(v) and len(str(v).split()) > 1:
            report["warnings"].append(
                f"'{key}' is a phrase (\"{str(v).strip()}\"): the engine only recognises single "
                f"words, so it will have no effect. Use one word (e.g. 'cage', 'road').")

    report["ok"] = not report["warnings"]
    return report


def format_report(report: dict) -> str:
    if report["ok"]:
        return "Everything looks filled in."
    return "Before you start, a few things look incomplete:\n- " + "\n- ".join(report["warnings"])
