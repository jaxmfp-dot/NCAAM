"""Booking business rules and event-simulation orchestration.

sim_bout() ties the fight engine, rankings, titles, and fighter records
together for one fight; sim_event() drives a whole card through it in order.
"""

import random
import sqlite3

import config
from engine import injuries, rankings, retirement, titles
from engine.fight.simulator import simulate_fight
from models import event as event_model
from models import fighter as fighter_model

FINISH_METHODS = ("KO", "TKO", "SUB")
KO_METHODS = ("KO", "TKO")


def book_bout(conn: sqlite3.Connection, event_id: int, fighter_a_id: int, fighter_b_id: int,
              rounds: int = 3, card_segment: str = "main", is_title_fight: bool = False,
              is_interim_title_fight: bool = False, is_number_one_contender: bool = False) -> int:
    if fighter_a_id == fighter_b_id:
        raise ValueError("A fighter can't be booked against themselves")

    fa = fighter_model.get_fighter(conn, fighter_a_id)
    fb = fighter_model.get_fighter(conn, fighter_b_id)
    if fa is None or fb is None:
        raise ValueError("Fighter not found")
    if fa["weight_class"] != fb["weight_class"] or fa["gender"] != fb["gender"]:
        raise ValueError(f"{fa['name']} ({fa['weight_class']}) and {fb['name']} ({fb['weight_class']}) "
                          f"aren't in the same division")
    for f in (fa, fb):
        if f["injury_status"] == "Injured":
            raise ValueError(f"{f['name']} is injured ({f['injury_description']}, "
                              f"expected back {f['injury_return_date']}) and can't be booked")
        if f.get("promotion", "UFC") != "UFC":
            raise ValueError(f"{f['name']} is not on the UFC roster ({f['promotion']}) -- sign them first")

    dupe = conn.execute(
        "SELECT id FROM bouts WHERE event_id = ? AND status = 'Scheduled' "
        "AND (fighter_a_id IN (?, ?) OR fighter_b_id IN (?, ?))",
        (event_id, fighter_a_id, fighter_b_id, fighter_a_id, fighter_b_id),
    ).fetchone()
    if dupe:
        raise ValueError("One of these fighters is already booked on this card")

    title_id = None
    if is_title_fight:
        title_id = titles.ensure_title(conn, fa["weight_class"], fa["gender"], is_interim=is_interim_title_fight)
        title = titles.get_title(conn, fa["weight_class"], fa["gender"], is_interim=is_interim_title_fight)
        if title["champion_id"] is not None and title["champion_id"] not in (fighter_a_id, fighter_b_id):
            champ_name = fighter_model.get_fighter(conn, title["champion_id"])["name"]
            label = "interim title" if is_interim_title_fight else "title"
            raise ValueError(f"The {label} is held by {champ_name} -- they must be part of this fight, "
                              f"or vacate the belt first")

    return event_model.add_bout(
        conn, event_id, fighter_a_id, fighter_b_id, fa["weight_class"], fa["gender"],
        rounds=rounds, card_segment=card_segment, is_title_fight=is_title_fight, title_id=title_id,
        is_interim_title_fight=is_interim_title_fight, is_number_one_contender=is_number_one_contender,
    )


def _finish_column(prefix: str, method: str) -> str:
    return {"KO": f"{prefix}_ko", "TKO": f"{prefix}_ko", "SUB": f"{prefix}_sub"}.get(method, f"{prefix}_dec")


def _apply_fighter_record(conn: sqlite3.Connection, fighter_id: int, winner_id: int | None,
                           method: str, is_title_fight: bool):
    if winner_id is None:
        conn.execute("UPDATE fighters SET draws = draws + 1 WHERE id = ?", (fighter_id,))
        momentum_delta = config.MOMENTUM_DRAW_DELTA
        popularity_delta = 0.0
    elif winner_id == fighter_id:
        col = _finish_column("wins", method)
        conn.execute(f"UPDATE fighters SET wins = wins + 1, {col} = {col} + 1 WHERE id = ?", (fighter_id,))
        momentum_delta = config.MOMENTUM_WIN_DELTA + (config.MOMENTUM_WIN_FINISH_BONUS if method in FINISH_METHODS else 0)
        popularity_delta = config.POPULARITY_WIN_DELTA + (config.POPULARITY_FINISH_BONUS if method in FINISH_METHODS else 0)
        if is_title_fight:
            popularity_delta += config.POPULARITY_TITLE_FIGHT_BONUS
    else:
        col = _finish_column("losses", method)
        conn.execute(f"UPDATE fighters SET losses = losses + 1, {col} = {col} + 1 WHERE id = ?", (fighter_id,))
        momentum_delta = config.MOMENTUM_LOSS_DELTA + (config.MOMENTUM_LOSS_FINISH_PENALTY if method in FINISH_METHODS else 0)
        popularity_delta = config.POPULARITY_LOSS_DELTA

    conn.execute(
        "UPDATE fighters SET momentum = MAX(?, MIN(?, momentum + ?)) WHERE id = ?",
        (config.MOMENTUM_MIN, config.MOMENTUM_MAX, momentum_delta, fighter_id),
    )
    conn.execute(
        "UPDATE fighters SET popularity = MAX(1, MIN(99, popularity + ?)) WHERE id = ?",
        (popularity_delta, fighter_id),
    )


def _apply_ko_loss_damage(conn: sqlite3.Connection, fighter_id: int):
    """A KO/TKO loss permanently chips away at durability -- accumulated head trauma."""
    conn.execute(
        "UPDATE fighters SET chin = MAX(?, chin - ?), toughness = MAX(?, toughness - ?) WHERE id = ?",
        (config.ATTR_MIN, config.KO_LOSS_CHIN_PENALTY, config.ATTR_MIN, config.KO_LOSS_TOUGHNESS_PENALTY, fighter_id),
    )


def sim_bout(conn: sqlite3.Connection, bout_id: int, seed: int | None = None) -> dict:
    bout = event_model.get_bout(conn, bout_id)
    if bout is None:
        raise ValueError(f"Bout {bout_id} not found")
    if bout["status"] == "Completed":
        raise ValueError("This bout has already been simulated")

    event = event_model.get_event(conn, bout["event_id"])
    fighter_a = fighter_model.get_fighter(conn, bout["fighter_a_id"])
    fighter_b = fighter_model.get_fighter(conn, bout["fighter_b_id"])
    rng = random.Random(seed)

    a_faced_rank = rankings.snapshot_rank(conn, fighter_b["id"], bout["weight_class"], bout["gender"], event["event_date"])
    b_faced_rank = rankings.snapshot_rank(conn, fighter_a["id"], bout["weight_class"], bout["gender"], event["event_date"])

    result = simulate_fight(fighter_a, fighter_b, rounds=bout["rounds"], seed=seed)
    winner_fighter_id = {"A": fighter_a["id"], "B": fighter_b["id"]}.get(result["winner_key"])
    result["winner_fighter_id"] = winner_fighter_id
    is_finish = result["method"] in FINISH_METHODS

    event_model.record_bout_result(conn, bout_id, result, a_faced_rank, b_faced_rank)
    _apply_fighter_record(conn, fighter_a["id"], winner_fighter_id, result["method"], bool(bout["is_title_fight"]))
    _apply_fighter_record(conn, fighter_b["id"], winner_fighter_id, result["method"], bool(bout["is_title_fight"]))

    loser_id = None
    if winner_fighter_id is not None:
        loser_id = fighter_b["id"] if winner_fighter_id == fighter_a["id"] else fighter_a["id"]
        if result["method"] in KO_METHODS:
            _apply_ko_loss_damage(conn, loser_id)

    for fid, fname in ((fighter_a["id"], fighter_a["name"]), (fighter_b["id"], fighter_b["name"])):
        is_loser = fid == loser_id
        injury = injuries.maybe_apply_fight_injury(conn, fid, fname, is_loser, is_finish, event["event_date"], rng)
        if injury:
            result.setdefault("injuries", []).append(injury)

    conn.commit()

    if bout["is_title_fight"] and winner_fighter_id is not None:
        title_result = titles.resolve_title_bout(conn, bout["title_id"], winner_fighter_id, event["event_date"])
        result["title_result"] = title_result
        event_model.set_title_change(conn, bout_id, title_result["title_changed"])

    if loser_id is not None:
        loser_row = fighter_model.get_fighter(conn, loser_id)
        if retirement.should_retire(conn, loser_row, event["event_date"], rng):
            retirement.retire_fighter(conn, loser_id, event["event_date"])
            result["retirement"] = {"id": loser_id, "name": loser_row["name"]}

    event_model.refresh_event_status(conn, bout["event_id"])
    return result


def sim_event(conn: sqlite3.Connection, event_id: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    scheduled = sorted(
        (b for b in event_model.list_bouts(conn, event_id) if b["status"] == "Scheduled"),
        key=lambda b: b["bout_order"],
    )
    return [sim_bout(conn, b["id"], seed=rng.randrange(2**32)) for b in scheduled]
