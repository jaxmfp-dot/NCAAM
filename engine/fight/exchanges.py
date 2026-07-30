"""Orchestrates a single exchange: who acts, what they try, and the
consequences (damage, position change, stats, commentary, finishes).

Every contested action goes through damage.contest_margin() on a pair of
effective (stamina/damage-adjusted) attribute ratings, so a fight result is
always traceable back to the two fighters' numbers.
"""

import random

import config
from engine.fight import commentary, damage
from engine.fight import positions as pos
from engine.fight.state import FightState

pick = commentary.pick

STRIKE_LABELS = {"punch": "punch", "kick": "kick", "knee": "knee strike",
                  "elbow": "elbow strike", "ground_punch": "ground strike"}
STRIKE_TECHNIQUE_ATTR = {"punch": "punch_technique", "kick": "kick_technique",
                          "knee": "knee_technique", "elbow": "elbow_technique",
                          "ground_punch": "punch_technique"}


def _power_value(kind: str, attacker) -> float:
    if kind in ("punch", "ground_punch"):
        return attacker.effective("punch_power", True)
    if kind == "kick":
        return attacker.effective("kick_power", True)
    if kind == "knee":
        return (attacker.effective("knee_technique", True) + attacker.effective("strength", True)) / 2
    if kind == "elbow":
        return (attacker.effective("elbow_technique", True) + attacker.effective("strength", True)) / 2
    return attacker.effective("punch_power", True)


def _time_str(match: FightState) -> str:
    elapsed = max(0.0, config.ROUND_SECONDS - match.clock)
    return f"{int(elapsed // 60)}:{int(elapsed % 60):02d}"


def _finish_ko(match: FightState, rng, winner_key: str, loser_key: str):
    w, l = match.get(winner_key).fighter["name"], match.get(loser_key).fighter["name"]
    match.log(pick(rng, commentary.KO_LINES).format(a=w, b=l))
    match.finish = {"type": "KO", "winner": winner_key, "round": match.round_num,
                     "time": _time_str(match), "method_detail": "Knockout"}


def _finish_tko(match: FightState, rng, winner_key: str, loser_key: str, reason: str):
    w, l = match.get(winner_key).fighter["name"], match.get(loser_key).fighter["name"]
    match.log(pick(rng, commentary.TKO_LINES).format(a=w, b=l))
    match.finish = {"type": "TKO", "winner": winner_key, "round": match.round_num,
                     "time": _time_str(match), "method_detail": f"TKO ({reason})"}


def _finish_sub(match: FightState, rng, winner_key: str, loser_key: str):
    w, l = match.get(winner_key).fighter["name"], match.get(loser_key).fighter["name"]
    match.log(pick(rng, commentary.SUB_TAP).format(a=w, b=l))
    match.finish = {"type": "SUB", "winner": winner_key, "round": match.round_num,
                     "time": _time_str(match), "method_detail": "Submission"}


def doctor_stoppage_check(match: FightState, rng) -> bool:
    for key in ("A", "B"):
        fs = match.get(key)
        if fs.cut_severity >= config.CUT_DOCTOR_STOPPAGE_THRESHOLD and rng.random() < config.CUT_DOCTOR_STOPPAGE_CHANCE:
            winner_key = pos.other(key)
            w = match.get(winner_key).fighter["name"]
            match.log(pick(rng, commentary.DOCTOR_STOPPAGE).format(a=w))
            match.finish = {"type": "TKO", "winner": winner_key, "round": match.round_num,
                             "time": "0:00", "method_detail": "TKO (Doctor Stoppage - Cuts)"}
            return True
    return False


def _followup_sequence(match: FightState, rng, attacker_key: str, defender_key: str):
    attacker, defender = match.get(attacker_key), match.get(defender_key)
    a_name, b_name = attacker.fighter["name"], defender.fighter["name"]
    n = rng.randint(config.FOLLOWUP_STRIKES_MIN, config.FOLLOWUP_STRIKES_MAX)
    for _ in range(n):
        match.log(pick(rng, commentary.FOLLOWUP_STRIKE).format(a=a_name, b=b_name))
        power = attacker.effective("punch_power", True)
        durability = ((defender.effective("chin", False) + defender.effective("toughness", False)) / 2
                       * config.FOLLOWUP_DEFENSE_MULT)
        dmg, _crit = damage.compute_strike_damage(rng, power, durability)
        defender.health = max(0.0, defender.health - dmg)
        attacker.cur()["sig_strikes_attempted"] += 1
        attacker.cur()["sig_strikes_landed"] += 1
        if defender.health <= 0:
            _finish_ko(match, rng, attacker_key, defender_key)
            return
        if not damage.followup_survives(rng, defender):
            _finish_tko(match, rng, attacker_key, defender_key, "unanswered strikes")
            return
    match.log(pick(rng, commentary.SURVIVE_FLURRY).format(a=a_name, b=b_name))


def _do_strike(match: FightState, rng, attacker_key: str, defender_key: str, kind: str, position_bonus: float = 0.0):
    attacker, defender = match.get(attacker_key), match.get(defender_key)
    a_name, b_name = attacker.fighter["name"], defender.fighter["name"]

    setup_pool = commentary.GROUND_STRIKE_SETUP if kind == "ground_punch" else commentary.STRIKE_SETUP
    match.log(pick(rng, setup_pool).format(a=a_name, b=b_name, strike=STRIKE_LABELS[kind]))
    attacker.cur()["sig_strikes_attempted"] += 1
    attacker.spend_stamina(config.STAMINA_COST_STRIKE_THROWN)

    technique = attacker.effective(STRIKE_TECHNIQUE_ATTR[kind], True) + position_bonus
    defense = defender.effective("striking_defense", False) + defender.effective("head_movement", False) * 0.5
    margin = damage.contest_margin(rng, technique, defense)
    landed = rng.random() < damage.logistic(margin)

    if not landed:
        match.log(pick(rng, commentary.STRIKE_MISS).format(a=a_name, b=b_name))
        return

    attacker.cur()["sig_strikes_landed"] += 1
    attacker.spend_stamina(config.STAMINA_COST_STRIKE_LANDED_BONUS)
    power = _power_value(kind, attacker)
    durability = defender.effective("chin", False) * 0.6 + defender.effective("toughness", False) * 0.4
    dmg, crit = damage.compute_strike_damage(rng, power, durability)
    defender.health = max(0.0, defender.health - dmg)
    match.log(pick(rng, commentary.STRIKE_LAND).format(a=a_name, b=b_name))

    cut_inc = damage.maybe_open_cut(rng, power)
    if cut_inc:
        defender.cut_severity = min(100.0, defender.cut_severity + cut_inc)
        match.log(pick(rng, commentary.CUT_LINES).format(a=a_name, b=b_name))

    if defender.health <= 0:
        _finish_ko(match, rng, attacker_key, defender_key)
        return

    if crit:
        match.log(pick(rng, commentary.STRIKE_CRIT).format(a=a_name, b=b_name))
        if defender.health <= config.KNOCKDOWN_HEALTH_THRESHOLD and defender.knockdown_count < config.MAX_KNOCKDOWNS_BEFORE_TKO:
            defender.knockdown_count += 1
            attacker.cur()["knockdowns"] += 1
            match.log(pick(rng, commentary.KNOCKDOWN).format(a=a_name, b=b_name))
            _followup_sequence(match, rng, attacker_key, defender_key)
            if match.is_over():
                return
            if defender.knockdown_count >= config.MAX_KNOCKDOWNS_BEFORE_TKO:
                _finish_tko(match, rng, attacker_key, defender_key, "three-knockdown rule")
                return
            match.position, match.top, match.clinch_control = pos.DISTANCE, None, None


def _do_takedown(match: FightState, rng, attacker_key: str, defender_key: str, from_clinch: bool = False):
    attacker, defender = match.get(attacker_key), match.get(defender_key)
    a_name, b_name = attacker.fighter["name"], defender.fighter["name"]

    match.log(pick(rng, commentary.TD_SETUP).format(a=a_name, b=b_name))
    attacker.cur()["takedowns_attempted"] += 1
    attacker.spend_stamina(config.STAMINA_COST_TAKEDOWN_ATTEMPT)

    bonus = 8.0 if from_clinch else 0.0
    off = attacker.effective("takedowns", True) * 0.8 + attacker.effective("strength", True) * 0.2 + bonus
    deff = defender.effective("takedown_defense", False) * 0.8 + defender.effective("strength", False) * 0.2
    margin = damage.contest_margin(rng, off, deff)
    landed = rng.random() < damage.logistic(margin)

    if landed:
        attacker.cur()["takedowns_landed"] += 1
        attacker.spend_stamina(config.STAMINA_COST_TAKEDOWN_LANDED_BONUS)
        new_position = pos.HALF_GUARD if margin > 20 else pos.GUARD
        match.position, match.top, match.clinch_control = new_position, attacker_key, None
        match.log(pick(rng, commentary.TD_LANDED).format(a=a_name, b=b_name,
                                                            position=pos.POSITION_NAMES[new_position]))
    else:
        match.log(pick(rng, commentary.TD_STUFFED).format(a=a_name, b=b_name))
        if not from_clinch:
            match.position = pos.DISTANCE


def _do_clinch_entry(match: FightState, rng, attacker_key: str, defender_key: str):
    attacker, defender = match.get(attacker_key), match.get(defender_key)
    a_name, b_name = attacker.fighter["name"], defender.fighter["name"]
    attacker.spend_stamina(config.STAMINA_COST_CLINCH_EXCHANGE * 0.5)

    off = attacker.effective("clinch_work", True)
    deff = defender.effective("clinch_work", False) * 0.7 + defender.effective("takedown_defense", False) * 0.3
    margin = damage.contest_margin(rng, off, deff)

    if rng.random() < damage.logistic(margin):
        match.position, match.clinch_control = pos.CLINCH, attacker_key
        match.log(pick(rng, commentary.CLINCH_ENTRY).format(a=a_name, b=b_name))
    else:
        match.log(pick(rng, commentary.CLINCH_FAIL).format(a=a_name, b=b_name))
        match.position = pos.DISTANCE


def _do_clinch_break(match: FightState, rng, actor_key: str, other_key: str):
    actor, other = match.get(actor_key), match.get(other_key)
    off = actor.effective("clinch_work", True) + 10
    deff = other.effective("clinch_work", False)
    margin = damage.contest_margin(rng, off, deff)

    if rng.random() < damage.logistic(margin):
        match.position, match.clinch_control = pos.DISTANCE, None
        match.log(pick(rng, commentary.CLINCH_BREAK).format(a=actor.fighter["name"], b=other.fighter["name"]))
    elif rng.random() < 0.3:
        match.clinch_control = other_key
        match.log(pick(rng, commentary.CLINCH_CONTROL_SHIFT).format(a=other.fighter["name"]))
    else:
        match.log(pick(rng, commentary.CLINCH_STAY))


def _distance_exchange(match: FightState, rng):
    a_score = _initiative_score(match.fighter_a)
    b_score = _initiative_score(match.fighter_b)
    attacker_key = "A" if damage.contest_margin(rng, a_score, b_score, variance=10) >= 0 else "B"
    defender_key = pos.other(attacker_key)
    attacker = match.get(attacker_key)

    strike_w = ((attacker.rating("punch_technique") + attacker.rating("kick_technique")
                 + attacker.rating("punch_power") + attacker.rating("kick_power")) / 4) * config.TENDENCY_STRIKE_MULT
    td_w = attacker.rating("takedowns") * config.TENDENCY_TAKEDOWN_MULT
    clinch_w = attacker.rating("clinch_work") * config.TENDENCY_CLINCH_MULT
    action = rng.choices(["strike", "takedown", "clinch"], weights=[max(1, strike_w), max(1, td_w), max(1, clinch_w)])[0]

    if action == "strike":
        kind = rng.choices(["punch", "kick"],
                            weights=[max(1, attacker.rating("punch_technique")), max(1, attacker.rating("kick_technique"))])[0]
        _do_strike(match, rng, attacker_key, defender_key, kind)
    elif action == "takedown":
        _do_takedown(match, rng, attacker_key, defender_key)
    else:
        _do_clinch_entry(match, rng, attacker_key, defender_key)


def _initiative_score(fs) -> float:
    return fs.effective("fight_iq", True) * 0.3 + fs.effective("speed", True) * 0.4 + fs.effective("agility", True) * 0.3


def _clinch_exchange(match: FightState, rng):
    actor_key = match.clinch_control or rng.choice(["A", "B"])
    other_key = pos.other(actor_key)
    actor = match.get(actor_key)

    strike_w = (actor.rating("knee_technique") + actor.rating("elbow_technique")) / 2 + 5
    td_w = actor.rating("takedowns") * 0.9 + actor.rating("clinch_work") * 0.3
    break_w = 25 + max(0, 60 - actor.rating("clinch_work")) * 0.4
    action = rng.choices(["strike", "takedown", "break"], weights=[max(1, strike_w), max(1, td_w), max(1, break_w)])[0]

    if action == "strike":
        kind = rng.choices(["knee", "elbow"],
                            weights=[max(1, actor.rating("knee_technique")), max(1, actor.rating("elbow_technique"))])[0]
        _do_strike(match, rng, actor_key, other_key, kind)
        if not match.is_over():
            match.get(other_key).spend_stamina(config.STAMINA_COST_CLINCH_EXCHANGE * 0.3)
    elif action == "takedown":
        _do_takedown(match, rng, actor_key, other_key, from_clinch=True)
    else:
        _do_clinch_break(match, rng, actor_key, other_key)


def _do_ground_strike(match: FightState, rng, top_key: str, bottom_key: str):
    bonus = pos.POSITION_DOMINANCE[match.position] * 2
    _do_strike(match, rng, top_key, bottom_key, "ground_punch", position_bonus=bonus)


def _do_advance(match: FightState, rng, top_key: str, bottom_key: str):
    top, bottom = match.get(top_key), match.get(bottom_key)
    off = top.effective("top_control", True)
    deff = bottom.effective("bottom_game", False) + bottom.effective("scrambling", False) * 0.3
    margin = damage.contest_margin(rng, off, deff)

    if rng.random() < damage.logistic(margin):
        idx = pos.ADVANCE_CHAIN.index(match.position)
        new_pos = pos.ADVANCE_CHAIN[min(idx + 1, len(pos.ADVANCE_CHAIN) - 1)]
        if new_pos == pos.MOUNT and rng.random() < 0.25:
            new_pos = pos.BACK_CONTROL
        match.position = new_pos
        match.log(pick(rng, commentary.ADVANCE).format(a=top.fighter["name"], position=pos.POSITION_NAMES[new_pos]))
    else:
        match.log(pick(rng, commentary.ADVANCE_FAIL).format(a=top.fighter["name"], b=bottom.fighter["name"]))


def _do_submission(match: FightState, rng, attacker_key: str, defender_key: str):
    attacker, defender = match.get(attacker_key), match.get(defender_key)
    a_name, b_name = attacker.fighter["name"], defender.fighter["name"]

    attacker.cur()["sub_attempts"] += 1
    attacker.spend_stamina(config.STAMINA_COST_SUB_ATTEMPT)
    match.log(pick(rng, commentary.SUB_ATTEMPT).format(a=a_name, b=b_name))

    off = attacker.effective("submissions", True)
    deff = defender.effective("submission_defense", False) + defender.effective("composure", False) * 0.2
    margin = damage.contest_margin(rng, off, deff, variance=config.SUB_CONTEST_VARIANCE)

    if margin > config.SUB_TAP_MARGIN_THRESHOLD:
        tap_chance = min(0.9, 0.15 + (margin - config.SUB_TAP_MARGIN_THRESHOLD) * config.SUB_TAP_CHANCE_SCALE)
        if rng.random() < tap_chance:
            _finish_sub(match, rng, attacker_key, defender_key)
            return
    match.log(pick(rng, commentary.SUB_DEFENDED).format(a=a_name, b=b_name))


def _do_sweep(match: FightState, rng, bottom_key: str, top_key: str):
    bottom, top = match.get(bottom_key), match.get(top_key)
    off = bottom.effective("bottom_game", True) * 0.6 + bottom.effective("scrambling", True) * 0.4
    deff = top.effective("top_control", False)
    margin = damage.contest_margin(rng, off, deff)
    prob = damage.logistic(margin) * 0.6

    if rng.random() < prob:
        match.top = bottom_key
        match.position = pos.GUARD
        match.log(pick(rng, commentary.SWEEP).format(a=top.fighter["name"], b=bottom.fighter["name"]))
    else:
        match.log(pick(rng, commentary.GROUND_SCRAMBLE_FAIL).format(
            a=top.fighter["name"], b=bottom.fighter["name"], position=pos.POSITION_LABELS[match.position]))


def _do_standup(match: FightState, rng, bottom_key: str, top_key: str):
    bottom, top = match.get(bottom_key), match.get(top_key)
    off = bottom.effective("scrambling", True)
    deff = top.effective("top_control", False)
    margin = damage.contest_margin(rng, off, deff)
    prob = damage.logistic(margin) * 0.5

    if rng.random() < prob:
        match.position, match.top, match.clinch_control = pos.DISTANCE, None, None
        match.log(pick(rng, commentary.STANDUP).format(a=top.fighter["name"], b=bottom.fighter["name"]))
    else:
        match.log(pick(rng, commentary.GROUND_SCRAMBLE_FAIL).format(
            a=top.fighter["name"], b=bottom.fighter["name"], position=pos.POSITION_LABELS[match.position]))


SUB_WEIGHT_BY_POSITION = {
    pos.GUARD: 0.15, pos.HALF_GUARD: 0.35, pos.SIDE_CONTROL: 0.6, pos.MOUNT: 1.0, pos.BACK_CONTROL: 1.3,
}
SWEEP_WEIGHT_BY_POSITION = {
    pos.GUARD: 1.0, pos.HALF_GUARD: 0.7, pos.SIDE_CONTROL: 0.35, pos.MOUNT: 0.15, pos.BACK_CONTROL: 0.2,
}
STANDUP_WEIGHT_BY_POSITION = {
    pos.GUARD: 0.5, pos.HALF_GUARD: 0.35, pos.SIDE_CONTROL: 0.2, pos.MOUNT: 0.1, pos.BACK_CONTROL: 0.15,
}


def _ground_exchange(match: FightState, rng):
    top_key = match.top
    bottom_key = pos.other(top_key)
    top, bottom = match.get(top_key), match.get(bottom_key)
    position = match.position

    options = [("strike", top.rating("top_control") * 0.5 + top.rating("punch_power") * 0.5 + 10)]
    if position in (pos.GUARD, pos.HALF_GUARD, pos.SIDE_CONTROL):
        options.append(("advance", top.rating("top_control") * 0.8 + top.rating("scrambling") * 0.2))
    options.append(("top_submit", top.rating("submissions") * SUB_WEIGHT_BY_POSITION[position] + 1))
    if position == pos.GUARD:
        options.append(("bottom_submit", bottom.rating("submissions") * 0.8 + 1))
    options.append(("sweep", (bottom.rating("bottom_game") * 0.6 + bottom.rating("scrambling") * 0.4)
                    * SWEEP_WEIGHT_BY_POSITION[position] + 1))
    options.append(("standup", bottom.rating("scrambling") * STANDUP_WEIGHT_BY_POSITION[position] + 1))

    names = [o[0] for o in options]
    weights = [max(1.0, o[1]) for o in options]
    action = rng.choices(names, weights=weights)[0]

    if action == "strike":
        _do_ground_strike(match, rng, top_key, bottom_key)
    elif action == "advance":
        _do_advance(match, rng, top_key, bottom_key)
    elif action == "top_submit":
        _do_submission(match, rng, top_key, bottom_key)
    elif action == "bottom_submit":
        _do_submission(match, rng, bottom_key, top_key)
    elif action == "sweep":
        _do_sweep(match, rng, bottom_key, top_key)
    elif action == "standup":
        _do_standup(match, rng, bottom_key, top_key)


def resolve_exchange(match: FightState, rng: random.Random) -> int:
    """Resolves one exchange in place, returns elapsed seconds."""
    position = match.position
    if position in (pos.DISTANCE, pos.CLINCH):
        elapsed = rng.randint(config.EXCHANGE_SECONDS_MIN, config.EXCHANGE_SECONDS_MAX)
    else:
        elapsed = rng.randint(config.GROUND_EXCHANGE_SECONDS_MIN, config.GROUND_EXCHANGE_SECONDS_MAX)

    for fs in (match.fighter_a, match.fighter_b):
        fs.regen_stamina(damage.stamina_regen_amount(fs))

    match.clock = max(0.0, match.clock - elapsed)

    if position == pos.CLINCH and match.clinch_control:
        match.get(match.clinch_control).cur()["control_seconds"] += elapsed
    elif position in pos.GROUND_POSITIONS and match.top:
        match.get(match.top).cur()["control_seconds"] += elapsed

    if position == pos.DISTANCE:
        _distance_exchange(match, rng)
    elif position == pos.CLINCH:
        _clinch_exchange(match, rng)
    else:
        _ground_exchange(match, rng)

    return elapsed
