"""Points-based divisional rankings: champion + top 15 contenders.

A fighter's score is the recency-weighted sum of points from their most
recent wins, each worth more for beating a higher-ranked opponent or
winning by finish. Because every query here is scoped to a fighter's
*current* weight_class, a fighter can never appear in two divisions at
once -- there's only one row for them to be found under.
"""

import sqlite3
from datetime import date, datetime

import config
from engine import titles


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _recency_weight(event_date: str, as_of: date) -> float:
    days = max(0, (as_of - _parse_date(event_date)).days)
    return 0.5 ** (days / config.RANKING_RECENCY_HALFLIFE_DAYS)


def rank_bonus(rank: int | None) -> float:
    if rank is None:
        return 0.0
    if rank == 0:
        return config.RANKING_CHAMPION_BEATEN_BONUS
    if rank <= 5:
        return config.RANKING_TOP5_BONUS
    if rank <= 10:
        return config.RANKING_TOP10_BONUS
    if rank <= 15:
        return config.RANKING_TOP15_BONUS
    return 0.0


def _seed_points(manual_rank_seed: int) -> float:
    frac = (manual_rank_seed - 1) / 14  # 0.0 at rank 1, 1.0 at rank 15
    return config.SEED_RANK_TOP_POINTS - frac * (config.SEED_RANK_TOP_POINTS - config.SEED_RANK_BOTTOM_POINTS)


def _seed_bonus(fighter_row: dict, as_of: date) -> float:
    seed, seed_date = fighter_row.get("manual_rank_seed"), fighter_row.get("manual_rank_seed_date")
    if seed is None or seed_date is None:
        return 0.0
    return _seed_points(seed) * _recency_weight(seed_date, as_of)


def _fighter_points(conn: sqlite3.Connection, fighter_id: int, as_of: date) -> float:
    rows = conn.execute(
        "SELECT b.fighter_a_id, b.a_faced_rank, b.b_faced_rank, b.method, e.event_date "
        "FROM bouts b JOIN events e ON e.id = b.event_id "
        "WHERE b.status = 'Completed' AND b.winner_id = ? "
        "ORDER BY e.event_date DESC LIMIT ?",
        (fighter_id, config.RANKING_MAX_FIGHTS_CONSIDERED),
    ).fetchall()

    total = 0.0
    for row in rows:
        was_a = row["fighter_a_id"] == fighter_id
        opponent_rank = row["a_faced_rank"] if was_a else row["b_faced_rank"]
        finish_bonus = config.RANKING_FINISH_BONUS if row["method"] in ("KO", "TKO", "SUB") else 0.0
        points = config.RANKING_WIN_BASE_POINTS + rank_bonus(opponent_rank) + finish_bonus
        total += points * _recency_weight(row["event_date"], as_of)
    return total


def compute_rankings(conn: sqlite3.Connection, weight_class: str, gender: str,
                      as_of_date: str | None = None) -> dict:
    as_of = _parse_date(as_of_date) if as_of_date else date.today()

    champion = titles.get_champion(conn, weight_class, gender, is_interim=False)
    interim_champion = titles.get_champion(conn, weight_class, gender, is_interim=True)
    champion_ids = {f["id"] for f in (champion, interim_champion) if f}

    roster = conn.execute(
        "SELECT * FROM fighters WHERE weight_class = ? AND gender = ? AND status = 'Active' "
        "AND promotion = 'UFC'",
        (weight_class, gender),
    ).fetchall()

    scored = []
    for row in roster:
        f = dict(row)
        if f["id"] in champion_ids:
            continue
        points = _fighter_points(conn, f["id"], as_of) + _seed_bonus(f, as_of)
        if points > 0:
            scored.append((points, f))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    contenders = [
        {"rank": i + 1, "fighter": f, "points": round(points, 1)}
        for i, (points, f) in enumerate(scored[:config.RANKING_TOP_N])
    ]

    return {"champion": champion, "interim_champion": interim_champion, "contenders": contenders}


def snapshot_rank(conn: sqlite3.Connection, fighter_id: int, weight_class: str, gender: str,
                   as_of_date: str | None = None) -> int | None:
    """0 = (interim or undisputed) champion, 1-15 = contender rank, None = unranked."""
    rankings = compute_rankings(conn, weight_class, gender, as_of_date)
    champion_ids = {f["id"] for f in (rankings["champion"], rankings["interim_champion"]) if f}
    if fighter_id in champion_ids:
        return 0
    for entry in rankings["contenders"]:
        if entry["fighter"]["id"] == fighter_id:
            return entry["rank"]
    return None
