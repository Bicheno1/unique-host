# tests/contradiction_cases.py — batch of 100 sentences with an expected label.
# The labels were written by the developer (there is no external ground truth): they serve
# to compare versions of the detector, not as an absolute judgment.
# NORMAL = must NOT flag a contradiction.  ABSURD = MUST flag it.

NORMAL = {
 "personas": [
  "the guard raises his sword", "the king speaks to the crowd", "the knight draws his sword",
  "the priest prays at the altar", "a thief steals the coin", "a hunter shoots an arrow",
  "a man climbs the tower", "the merchant sells a sword", "a soldier draws his blade",
  "a woman opens the door", "a child laughs in the garden", "the innkeeper pours a drink",
  "a girl smiles at you", "the queen watches the fire", "a bandit attacks the merchant",
  "the blacksmith hammers the steel", "a monk walks toward the gate", "the servant carries a tray",
  "a farmer plants the seeds", "the captain shouts an order", "the healer treats the wound",
  "a stranger whispers your name", "the mayor signs the letter", "a boy throws a stone",
 ],
 "animals": [
  "a wolf lunges at the child", "the dog barks at the stranger", "a cat sleeps on the wall",
  "the horse gallops across the field", "a snake slithers past", "the fish swims in the river",
  "a cow grazes near the barn", "the wolf howls at the moon", "a pig roots in the mud",
  "the mouse runs into the wall", "a bear charges at the child", "the deer walks through the forest",
 ],
 "voladores_y_fantasia": [
  "a bird flies over the wall", "the duck flies over the lake", "an eagle flies above the tower",
  "the crow flies toward the castle", "the bat flies out of the cave", "the dragon flies over the village",
  "the griffin flies over the mountain", "the fairy flies through the window", "the wizard flies over the city",
  "a hawk flies across the valley", "the owl flies through the night",
 ],
 "figurative_objects": [
  "the sword sings a song to the king", "the door groans in the wind", "the wind whispers your name",
  "the fire dances on the wall", "the old house remembers the war", "the river laughs at the stones",
  "the storm swallows the ship", "the mountain watches the village", "the blade whispers to the thief",
  "the shadow crawls across the floor",
 ],
 "negated_questions_conditionals": [
  "dogs don't fly", "fish do not walk", "a cow cannot fly", "can a dog fly?",
  "if the wolf flew, we would be safe", "does a fish walk?", "the horse never flies", "no dog flies",
 ],
 "various_scenes": [
  "a bandit steps out of the bushes, blade drawn", "the guard walks toward the gate",
  "a bandit steps out of the bushes, sword drawn", "we enter the dark tavern",
  "the traveler rests by the fire", "a merchant sells rope to the sailors",
  "you look at the stars", "the children run to the river",
 ],
}

ABSURD = [
 "a dog flies over the wall", "the fish walks along the shore", "a cow flies across the field",
 "the wolf flies over the river", "a horse flies to the moon", "the cat flies through the window",
 "a sheep flies over the fence", "the rabbit flies over the hill", "a pig flies over the barn",
 "the mouse flies across the room", "a shark walks into the tavern", "the frog flies over the pond",
 "a snake flies over the wall", "the bear flies toward the child", "a deer flies over the road",
 "the fox flies through the trees", "the lion flies at the guard", "a goat flies above the crowd",
 "the trout walks on the shore", "the elephant flies over the tower",
]

def all_normal():
    return [(t, g) for g, lst in NORMAL.items() for t in lst]
