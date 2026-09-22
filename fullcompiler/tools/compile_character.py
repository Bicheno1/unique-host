# tools/compile_character.py — UNIQUE HOST
# Compiles an answers file (JSON {question_key: value}) into a character.json
# and prints the missing-sections report.  It does the same thing the UI does,
# but repeatable from the terminal (useful for tests and for regenerating
# characters when the questionnaire grows):
#
#   python tools/compile_character.py characters/delia_answers.json characters/delia_adventurer_v3.json
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from questionnaire.questionnaire import build_character_json
from questionnaire.completeness import check_completeness, format_report

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    answers = json.load(open(src, encoding="utf-8"))
    print(format_report(check_completeness(answers)))
    character = build_character_json(answers)
    json.dump(character, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{dst}: {len(character['concepts_seed'])} conceptos, "
          f"{len(character['tag_values_seed']['somatic'])} tags")
