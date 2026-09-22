# tools/build_extra_categories.py — UNIQUE HOST
#
# Generates lexicon_db/db_category_words_extra.py: NEW likes-tree nodes for
# the lexicon words that no question reached.
# Needs nltk + wordnet.
#
#   python tools/build_extra_categories.py
#
# Rules:
#  1. Inflected forms (plurals) of already-covered words -> added to the SAME
#     branches as their lemma (0 new questions).
#  2. Proper names (WordNet instance hypernym) -> excluded on purpose:
#     a name has no per-category valence (for individuals there is
#     valued_bond / core_fear / core_comfort).
#  3. The rest is grouped by WordNet hyponyms (BUCKETS, first matching rule
#     wins) or by manual lists (emotions).
#  4. Whatever makes no sense to ask about (units, geometry, meta-words,
#     mixed polarity) is left out and listed in the report.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import defaultdict
from nltk.corpus import wordnet as wn
from lexicon_db.db_lexicon import LEXICON
from lexicon_db.db_category_words import CATEGORY_WORDS_BASE as CATEGORY_WORDS
from questionnaire.questionnaire import WORLD_GROUPS

# (path, question, allowed lexnames or None, hypernym anchors)
BUCKETS = [
 (("non_biological","violence_crime"),
  "How do they feel about violence, crime and cruelty (e.g. murder, assault, torture)? (1=dislike/avoid, 10=drawn to it)",
  None, ["crime.n.01","violence.n.01","violence.n.03","killing.n.02","murder.n.01","attack.n.01","aggression.n.02","cruelty.n.02","abuse.n.01","genocide.n.01","assault.n.01"]),
 (("non_biological","war_conflict"),
  "How do they feel about war, battles and open conflict (e.g. campaign, conflict, revolution)? (1=dislike/avoid, 10=drawn to it)",
  None, ["military_action.n.01","battle.n.01","war.n.01","fight.n.02","revolution.n.01","siege.n.01"]),
 (("non_biological","illness_injury"),
  "How do they feel about illness, injury and physical suffering (e.g. disease, wounds, fatigue)? (1=dislike/avoid, 10=drawn to it)",
  None, ["illness.n.01","disease.n.01","injury.n.01","disorder.n.01","symptom.n.01","death.n.01","microorganism.n.01"]),
 (("non_biological","misfortune"),
  "How do they feel about misfortune, accidents and setbacks (e.g. collision, defeat, trouble)? (1=dislike/avoid, 10=drawn to it)",
  None, ["defeat.n.01","failure.n.01","disaster.n.01","accident.n.01","misfortune.n.01","collision.n.01"]),
 (("non_biological","success_triumph"),
  "How do they feel about success, victories and improvement (e.g. victory, achievement, progress)? (1=dislike, 10=love)",
  None, ["success.n.01","victory.n.01","improvement.n.01","achievement.n.01","progress.n.01"]),
 (("non_biological","freedom"),
  "How do they feel about freedom and independence? (1=dislike/avoid, 10=drawn to it)",
  None, ["freedom.n.01","independence.n.01","liberty.n.01"]),
 (("non_biological","money_wealth"),
  "How do they feel about money, wealth and valuables (e.g. income, assets, gifts, currency)? (1=dislike, 10=love)",
  ["possession"], ["medium_of_exchange.n.01","currency.n.01","income.n.01","assets.n.01","gift.n.01","financial_gain.n.01","net_income.n.01","wealth.n.01"]),
 (("non_biological","debts_costs"),
  "How do they feel about debts, fees, taxes and costs (e.g. loans, expenses, fines)? (1=dislike/avoid, 10=drawn to it)",
  ["possession"], ["liabilities.n.01","cost.n.01","outgo.n.01","tax.n.01","levy.n.01"]),
 (("non_biological","law_authority"),
  "How do they feel about laws, rules and formal orders (e.g. commands, contracts, regulations)? (1=dislike/avoid, 10=respect)",
  None, ["legal_document.n.01","law.n.01","command.n.01","rule.n.01","social_control.n.01","due_process.n.01","duty.n.01","regulation.n.01"]),
 (("non_biological","institutions"),
  "How do they feel about governments, institutions and big organizations (e.g. council, government, corporation)? (1=distrust, 10=trust)",
  ["group"], ["institution.n.01","administrative_unit.n.01","government.n.01","establishment.n.02","agency.n.01","legislature.n.01","council.n.02"]),
 (("non_biological","armed_forces"),
  "How do they feel about armies and armed forces (e.g. troops, patrols, military units)? (1=distrust/dislike, 10=admire)",
  None, ["military_unit.n.01","army_unit.n.01","military_service.n.01","force.n.04","armed_forces.n.01"]),
 (("non_biological","stories_art_music"),
  "How do they feel about stories, art and music (e.g. fiction, songs, paintings)? (1=dislike, 10=love)",
  ["communication","cognition","act","object"], ["music.n.01","fiction.n.01","literature.n.01","musical_composition.n.01","painting.n.01","drama.n.01","dance.n.01","poem.n.01","story.n.01"]),
 (("non_biological","symbols_omens"),
  "How do they feel about symbols, signs and omens (e.g. runes, sigils, prophecies)? (1=uneasy, 10=fascinated)",
  None, ["symbol.n.01","prophecy.n.01","omen.n.01","charm.n.02","rune.n.01","sigil.n.01"]),
 (("non_biological","science_knowledge"),
  "How do they feel about science and scholarly knowledge (e.g. biology, logic, mechanics)? (1=dislike, 10=love)",
  ["cognition"], ["knowledge_domain.n.01","discipline.n.01","science.n.01","natural_science.n.01","scientific_knowledge.n.01"]),
 (("non_biological","faith_ethics"),
  "How do they feel about faith, ethics and matters of conscience (e.g. religion, morals, conscience)? (1=uneasy, 10=drawn to it)",
  ["cognition","motive","attribute","communication"], ["religion.n.01","morality.n.01","ethics.n.01","conscience.n.01","faith.n.01","moral_philosophy.n.01","religious_belief.n.01"]),
 (("non_biological","ideas_plans"),
  "How do they feel about ideas, imagination and making plans (e.g. schemes, predictions, goals)? (1=dislike, 10=love)",
  ["cognition","motive"], ["plan.n.01","goal.n.01","imagination.n.01","incentive.n.01","hypothesis.n.02"]),
 (("non_biological","work_business"),
  "How do they feel about work and business (e.g. jobs, trade, deals)? (1=dislike/avoid, 10=drawn to it)",
  ["act"], ["occupation.n.01","commerce.n.01","transaction.n.01","job.n.02","trade.n.01"]),
 (("non_biological","games_festivities"),
  "How do they feel about games, sports and celebrations (e.g. contests, parties, festivals)? (1=dislike, 10=love)",
  None, ["game.n.01","sport.n.01","diversion.n.01","social_event.n.01","ceremony.n.01","celebration.n.01"]),
 (("non_biological","travel_journeys"),
  "How do they feel about travel and journeys (e.g. trips, voyages, moving on)? (1=dislike, 10=love)",
  ["act","event"], ["travel.n.01","journey.n.01","motion.n.06","change_of_location.n.01"]),
 (("non_biological","virtues_strengths"),
  "How do they feel about virtues and strengths of character (e.g. commitment, solidarity, courage)? (1=dislike, 10=admire)",
  ["attribute"], ["morality.n.01","trait.n.01","virtue.n.01"]),
 (("non_biological","metals_materials"),
  "How do they feel about metals and raw materials (e.g. iron, glass, clay, oil)? (1=indifferent/dislike, 10=drawn to it)",
  ["substance"], ["metallic_element.n.01","metal.n.01","alloy.n.01","mineral.n.01","rock.n.01","glass.n.01","plastic.n.01","fuel.n.01"]),
 (("non_biological","chemicals_waste"),
  "How do they feel about chemicals, waste and impure substances (e.g. toxins, sewage, dust)? (1=dislike/avoid, 10=drawn to it)",
  ["substance"], ["waste.n.01","body_waste.n.01","toxin.n.01","poison.n.01","pollutant.n.01","drug.n.01"]),
 (("non_biological","seasons_holidays"),
  "How do they feel about seasons and holidays (e.g. autumn, holidays, months of the year)? (1=dislike, 10=love)",
  ["time"], ["season.n.02","holiday.n.01","calendar_month.n.01","time_off.n.01","leisure.n.01"]),
]
# Emotions: manual lists (no WordNet anchor separates polarity).
EMOTIONS = [
 (("non_biological","warm_emotions"),
  "How do they feel about warm emotions and desire (e.g. love, joy, pride, hope, passion)? (1=dislike/avoid, 10=drawn to it)",
  ["affection","ambition","appetite","attachment","awe","compassion","delight","desire","desires","enjoyment","enthusiasm","excitement","forgiveness","gratitude","hope","hopes","humour","joy","liking","love","passion","pleasure","pride","relief","satisfaction"]),
 (("non_biological","dark_emotions"),
  "How do they feel about dark emotions (e.g. fear, rage, shame, grief, hatred)? (1=dislike/avoid, 10=drawn to it)",
  ["alarm","anger","disappointment","distress","envy","fear","fears","frustration","fury","grief","harassment","hatred","horror","outrage","panic","pity","rage","resignation","sadness","shame","shock","spite","stab","surrender","terror","torture"]),
]
# Leftovers that are added to EXISTING branches (same meaning, missing word).
LEFTOVER_TO_EXISTING = {
 ("biological","animal"):  ("biological",["animal"]),
 ("biological","plant"):   ("biological",["plant"]),
 ("non_biological","food"):("non_biological",["food"]),
 ("non_biological","weather"):("non_biological",["weather"]),
}
# New branches for biological words.
BIO_BUCKETS = [
 (("biological","crowds_groups"),
  "How do they feel about crowds, tribes and groups of people (e.g. crowd, faction, choir, allies)? (1=distrust/avoid, 10=drawn to it)"),
]
EXCLUDED_LEXNAMES = {"quantity","shape","relation","abstract","place","object","time","attribute","communication","cognition","state","act","event","group"}  # only if they did not fall into a bucket

# Abbreviations / stray names / odd senses that WordNet lets through.
NOISE = {"las","rico","hans","han","beth","fda","sept","jan","guinea","pics","doubles","founder",
         "spots","serial","stops","outs","slam","fare","aids","default","returns","draft","cards",
         "tactics","communications","killing","hearts","alpha","beta","oscar","font","citation",
         "shifts","closure","completion","elevation","stroke","fade","accommodation","luxury",
         "privacy","occasions","voices","collapse","sting","complaint","premiere"}

def _syns(w, cat):
    ss = [s for s in wn.synsets(w, "n") if s.lexname() == "noun."+cat]
    return ss or wn.synsets(w, "n")

def _anc(w, cat):
    """Hypernyms of the FIRST WordNet sense, and only if that sense belongs to the
    category the lexicon assigned it (same criterion the lexicon used, without
    jumping to odd senses that bring homonyms)."""
    ss = wn.synsets(w, "n")
    if not ss or ss[0].lexname() != "noun." + cat:
        return set()
    return {h.name() for p in ss[0].hypernym_paths() for h in p}

def main():
    covered = set(w for ws in CATEGORY_WORDS.values() for w in ws)
    covered |= {n for g in WORLD_GROUPS.values() for n, *_ in g["words"]} | {"family", "animal"}
    unc = {w: n for w, n in LEXICON.items() if w not in covered}

    extra = defaultdict(list); labels = {}; report = {"proper": [], "inflected": [], "excluded": []}
    lem = lambda w: wn.morphy(w, "n") or w

    # 2. proper names
    rest = {}
    for w, n in unc.items():
        ss = _syns(w, n["category"])
        if ss and (ss[0].instance_hypernyms() or w[0].isupper()):
            report["proper"].append(w)
        else:
            rest[w] = n

    # 1. inflected forms of covered words -> the lemma's branch (further down, once extras are built)
    inflected = {w for w in rest if lem(w) != w and lem(w) in covered}
    rest = {w: n for w, n in rest.items() if w not in inflected}

    # 3a. manual emotions
    placed = set()
    for path, label, words in EMOTIONS:
        labels[path] = label
        for w in words:
            if w in rest: extra[path].append(w); placed.add(w)
    # 3b. buckets by hyponyms
    for w, n in sorted(rest.items()):
        if len(w) < 3 or w in NOISE: continue
        if w in placed or n["node_type"] == "action" or n["node_type"] == "quality": continue
        cat = n["category"]
        if cat == "emotion": continue
        anc = None
        for path, label, cats, anchors in BUCKETS:
            if cats and cat not in cats: continue
            if anc is None: anc = _anc(w, cat)
            if anc & set(anchors):
                labels[path] = label; extra[path].append(w); placed.add(w); break
    # 3c. biological: groups of people
    for path, label in BIO_BUCKETS:
        for w, n in sorted(rest.items()):
            if w not in placed and n["node_type"] == "biological" and n["category"] == "group":
                labels[path] = label; extra[path].append(w); placed.add(w)
    # 3d. leftovers into existing branches (same type/category)
    for path, (top, cats) in LEFTOVER_TO_EXISTING.items():
        for w, n in sorted(rest.items()):
            if w not in placed and n["node_type"] == top and n["category"] in cats:
                extra[path].append(w); placed.add(w)

    # 1. inflected forms: same branches as the lemma (old + new)
    all_paths = defaultdict(list)
    for path, ws in list(CATEGORY_WORDS.items()) + list(extra.items()):
        for w in ws: all_paths[w].append(path)
    for w in sorted(inflected):
        for path in all_paths.get(lem(w), []):
            if path[0] == LEXICON[w]["node_type"] and w not in extra[path]:
                extra[path].append(w)
        report["inflected"].append(w)

    still = sorted(set(unc) - set(report["proper"]) - placed - inflected)
    report["excluded"] = still
    return dict(extra), labels, report

if __name__ == "__main__":
    extra, labels, report = main()
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lexicon_db", "db_category_words_extra.py")
    with open(out, "w", encoding="utf-8") as f:
        f.write('"""db_category_words_extra.py — generated by tools/build_extra_categories.py\n'
                'New likes-tree branches (+ missing words in old branches).\n'
                'Do not edit by hand: regenerate with the tool."""\n\n')
        f.write("CATEGORY_WORDS_EXTRA = {\n")
        for path, ws in sorted(extra.items()):
            f.write(f"    {path!r}: {sorted(set(ws))!r},\n")
        f.write("}\n\nEXTRA_LABELS = {\n")
        for path, lab in sorted(labels.items()):
            f.write(f"    {path!r}: {lab!r},\n")
        f.write("}\n")
    json.dump(report, open("/tmp/extra_report.json", "w"))
    print("written", out)
    for p, ws in sorted(extra.items()): print(f"{len(set(ws)):4} {'/'.join(p)}")
    print({k: len(v) for k, v in report.items()})
