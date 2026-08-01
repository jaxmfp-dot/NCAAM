"""Templated play-by-play text. Pools give variety; callers assemble 2-4 lines
per exchange by picking from the pools relevant to what just happened."""

import random

from engine.fight import positions as pos

STRIKE_SETUP = [
    "{a} circles and fires a {strike} at {b}.",
    "{a} looks to close the distance behind a {strike}.",
    "{a} feints low, then lets a {strike} go.",
    "{a} steps in behind a {strike}.",
    "{a} times the range and throws a {strike}.",
]
STRIKE_LAND = [
    "It lands flush on {b}!",
    "{b} eats it clean.",
    "The shot connects and {b} winces.",
    "Direct hit -- {b} felt that one.",
    "{a} finds the mark.",
]
STRIKE_CRIT = [
    "{b}'s legs wobble!",
    "That one buzzed {b} badly!",
    "{b} is clearly hurt!",
    "A visibly shaken {b} tries to reset.",
]
STRIKE_MISS = [
    "{b} slips it.",
    "{b} rolls with the shot and it grazes.",
    "{a} comes up empty as {b} pulls back.",
    "{b} covers up and blocks the brunt of it.",
    "{b} times a step back and it falls short.",
]
KNOCKDOWN = [
    "{b} crashes to the canvas!",
    "{b} is down!",
    "Down goes {b}!",
]
FOLLOWUP_STRIKE = [
    "{a} pounces with follow-up shots!",
    "{a} swarms, looking for the finish!",
    "{a} unloads on a hurt {b}!",
]
KO_LINES = [
    "{a} lands the finishing blow and the fight is waved off -- {b} is out cold!",
    "The referee jumps in immediately. {b} is done. {a} wins by knockout!",
    "{a} closes the show emphatically!",
]
TKO_LINES = [
    "{b} is no longer intelligently defending -- the referee steps in. TKO, {a}!",
    "The corner and the referee have seen enough. {a} wins by TKO!",
]
CUT_LINES = [
    "{b} has been opened up -- blood starts to flow.",
    "A cut appears on {b}.",
    "{a}'s shot has cut {b} open.",
]
DOCTOR_STOPPAGE = [
    "The doctor takes a long look at the cut and waves it off -- TKO, {a}, doctor stoppage.",
]

TD_SETUP = [
    "{a} shoots for a takedown.",
    "{a} looks to change levels.",
    "{a} ducks under, hunting for the legs.",
]
TD_LANDED = [
    "{a} changes levels and drives through for the takedown!",
    "{a} times the entry and puts {b} on the mat.",
    "{a} chains together a takedown, landing in {position}.",
]
TD_STUFFED = [
    "{b} sprawls and stuffs it.",
    "{a} shoots but {b}'s base is too good.",
    "{b} defends well and the two reset at distance.",
]
TD_REVERSED = [
    "{b} defends the shot and scrambles on top!",
]

CLINCH_ENTRY = [
    "{a} closes in and ties {b} up in the clinch.",
    "{a} grabs a collar tie and pulls {b} into the clinch.",
    "{a} presses forward into the clinch.",
]
CLINCH_FAIL = [
    "{b} frames off and keeps the fight at range.",
    "{a} reaches for the clinch but {b} circles away.",
]
CLINCH_STRIKE = [
    "{a} rips a knee up the middle.",
    "{a} lands a short elbow in the clinch.",
    "{a} cracks a knee to the body.",
]
CLINCH_BREAK = [
    "{b} pushes off and the fighters reset at range.",
    "{a} disengages from the clinch.",
    "The fighters separate and reset at distance.",
]
CLINCH_CONTROL_SHIFT = [
    "{a} works the underhook and takes control of the clinch.",
]
CLINCH_STAY = [
    "The two remain tied up against the fence.",
    "Neither fighter can create the separation.",
]

GROUND_STRIKE_SETUP = [
    "{a} postures up and looks to land a {strike}.",
    "{a} opens up with a {strike} from the top.",
    "{a} fires down a {strike}.",
]
GROUND_STRIKE = [
    "{a} lands a heavy shot {position_phrase}.",
    "{a} postures up and drops a punch.",
    "{a} peppers {b} with strikes from the top.",
]
ADVANCE = [
    "{a} works to {position}.",
    "{a} improves position, moving to {position}.",
    "{a} slides through to {position}.",
]
ADVANCE_FAIL = [
    "{b} frames and denies the pass.",
    "{a} looks to advance but {b}'s guard holds.",
]
SWEEP = [
    "{b} sweeps and the position reverses!",
    "{b} rolls {a} over and takes top position!",
]
STANDUP = [
    "Both fighters scramble back up to the feet.",
    "{b} works back to the feet and the action resets at distance.",
    "The fighters are back standing.",
]
GROUND_SCRAMBLE_FAIL = [
    "{b} tries to escape but {a} maintains {position}.",
    "{a} holds the position down.",
]

SUB_ATTEMPT = [
    "{a} locks in a submission attempt!",
    "{a} goes hunting for a finish!",
    "{a} threatens with a tight submission attempt.",
]
SUB_DEFENDED = [
    "{b} defends and escapes the threat.",
    "{b} stays calm and works free.",
    "{b} pops the hips out and survives.",
]
SUB_TAP = [
    "{b} has no choice but to tap!",
    "{a} gets the tap! It's over!",
]
SURVIVE_FLURRY = [
    "{b} survives the barrage and covers up until the danger passes.",
    "{b} rides out the storm and the fighters reset at distance.",
]


def pick(rng: random.Random, pool: list[str]) -> str:
    return rng.choice(pool)


def position_phrase(position: str) -> str:
    return pos.POSITION_LABELS.get(position, position)
