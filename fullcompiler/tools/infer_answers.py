# tools/infer_answers.py — UNIQUE HOST
# Reverse path: character.json -> questionnaire answers (approximate).
# Used to MIGRATE an old character when the questionnaire grows: its answers
# are inferred, the new questions are added and it is recompiled.
#   python tools/infer_answers.py characters/delia_adventurer_v2.json characters/delia_answers.json
#
# Limits (honest ones): the tree answers are inferred by fitting (each node's
# 1-10 value that best reproduces its words' final values); nodes with no
# observed words are left UNANSWERED. Texts the compiler does not store
# verbatim (e.g. purpose_source) cannot be recovered.
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from questionnaire.questionnaire import WORLD_GROUPS
from questionnaire.tree_questionnaire import _question_key
from questionnaire.valence import refine_chain
from lexicon_db.db_category_words import CATEGORY_WORDS

GROUP_PROBE = {"people_opinion": "person", "animals_opinion": "fish", "environment_opinion": "room",
               "world_objects_opinion": "food", "supernatural_opinion": "ghost",
               "fantasy_opinion": "wizard", "fantasy_objects_opinion": "potion",
               "family_opinion": "family"}

def infer(char: dict) -> dict:
    ans, b = {}, char["base_state"]
    for ax in ("V", "I", "Lv", "Gv"): ans[f"fort_{ax}"] = b["somatic"][ax] / 5
    for ax in ("P", "A", "Er", "Rr"): ans[f"fort_{ax}"] = b["mental"][ax] / 5
    for cat, v in char["category_bias"].items(): ans[f"bias_{cat}"] = v
    for cat, gs in char["chemical_gains"].items():
        for ax, v in gs.items(): ans[f"gain_{cat}_{ax}"] = v
    idv = char["core_identity_rules"]["host_identity"]["value"]
    ans.update(name=idv["name"], age=idv["age"], height_cm=int(str(idv["height"]).replace("cm", "")),
               physical_traits=idv.get("traits", ""))
    for src, dst in (("father", "father_name"), ("mother", "mother_name"), ("pet", "pet_name")):
        if idv.get(src): ans[dst] = idv[src]
    cr = char["core_identity_rules"]
    if "custom_fear" in cr: ans["core_fear"] = cr["custom_fear"]["concepts"][0]
    if "custom_comfort" in cr: ans["core_comfort"] = cr["custom_comfort"]["concepts"][0]
    if "custom_friend" in cr: ans["friend_name"] = cr["custom_friend"]["value"]["name"]
    S = {k[9:]: x["V"] / 5 for k, x in char["tag_values_seed"]["somatic"].items()}
    for gk, probe in GROUP_PROBE.items():
        if probe in S: ans[gk] = S[probe]
    paths = sorted(CATEGORY_WORDS, key=len)
    vals = {p: 5.0 for p in paths}
    words_in = {p: [w for w in CATEGORY_WORDS[p] if w in S] for p in paths}
    def final(w):
        ent = sorted((len(p), vals[p]) for p in paths if w in CATEGORY_WORDS[p])
        v = [x for _, x in ent]
        return refine_chain(v) if len(v) > 1 else v[0]
    for _ in range(4):
        for p in paths:
            ws = words_in[p]
            if not ws: continue
            vals[p] = float(min(range(1, 11), key=lambda v: sum(
                abs(_final_with(w, vals, p, v, paths) - S[w]) for w in ws)))
    for p in paths:
        if words_in[p]: ans[_question_key(p)] = vals[p]
    return ans

def _final_with(w, vals, p, v, paths):
    ent = sorted((len(q), float(v) if q == p else vals[q]) for q in paths if w in CATEGORY_WORDS[q])
    vv = [x for _, x in ent]
    return refine_chain(vv) if len(vv) > 1 else vv[0]

if __name__ == "__main__":
    out = infer(json.load(open(sys.argv[1], encoding="utf-8")))
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{sys.argv[2]}: {len(out)} respuestas inferidas")
