"""Year-in-review reporting: title changes, breakout prospects, retirements."""

import sqlite3
from datetime import date

import config
from models.fighter import compute_age, record_string


def year_in_review(conn: sqlite3.Connection, year: int) -> dict:
    start, end = f"{year}-01-01", f"{year}-12-31"

    title_rows = conn.execute(
        "SELECT b.*, e.event_date, t.weight_class, t.gender, t.is_interim, "
        "fa.name AS fighter_a_name, fb.name AS fighter_b_name "
        "FROM bouts b "
        "JOIN events e ON e.id = b.event_id "
        "JOIN titles t ON t.id = b.title_id "
        "JOIN fighters fa ON fa.id = b.fighter_a_id "
        "JOIN fighters fb ON fb.id = b.fighter_b_id "
        "WHERE b.is_title_fight = 1 AND b.title_change = 1 AND b.status = 'Completed' "
        "AND e.event_date BETWEEN ? AND ? ORDER BY e.event_date",
        (start, end),
    ).fetchall()

    title_changes = []
    for row in title_rows:
        d = dict(row)
        is_a_winner = d["winner_id"] == d["fighter_a_id"]
        title_changes.append({
            "event_date": d["event_date"], "weight_class": d["weight_class"], "gender": d["gender"],
            "is_interim": bool(d["is_interim"]),
            "winner_name": d["fighter_a_name"] if is_a_winner else d["fighter_b_name"],
            "loser_name": d["fighter_b_name"] if is_a_winner else d["fighter_a_name"],
            "method_detail": d["method_detail"],
        })

    bout_rows = conn.execute(
        "SELECT b.fighter_a_id, b.fighter_b_id, b.winner_id FROM bouts b "
        "JOIN events e ON e.id = b.event_id "
        "WHERE b.status = 'Completed' AND e.event_date BETWEEN ? AND ?",
        (start, end),
    ).fetchall()
    wins, losses = {}, {}
    for row in bout_rows:
        a, b, winner = row["fighter_a_id"], row["fighter_b_id"], row["winner_id"]
        if winner is None:
            continue
        loser = b if winner == a else a
        wins[winner] = wins.get(winner, 0) + 1
        losses[loser] = losses.get(loser, 0) + 1

    as_of = date(year, 12, 31)
    breakout = []
    for row in conn.execute("SELECT * FROM fighters WHERE status = 'Active'").fetchall():
        f = dict(row)
        age = compute_age(f["dob"], as_of)
        w, losses_this_year = wins.get(f["id"], 0), losses.get(f["id"], 0)
        if age <= config.BREAKOUT_PROSPECT_MAX_AGE and w >= config.BREAKOUT_PROSPECT_MIN_WINS and losses_this_year == 0:
            breakout.append({"id": f["id"], "name": f["name"], "weight_class": f["weight_class"],
                              "gender": f["gender"], "age": age, "wins_this_year": w,
                              "popularity": f["popularity"]})
    breakout.sort(key=lambda x: (x["wins_this_year"], x["popularity"]), reverse=True)

    retired_rows = conn.execute(
        "SELECT * FROM fighters WHERE retired_date BETWEEN ? AND ? ORDER BY retired_date", (start, end)
    ).fetchall()
    retirements = [
        {"id": r["id"], "name": r["name"], "weight_class": r["weight_class"], "gender": r["gender"],
         "record": record_string(dict(r)), "retired_date": r["retired_date"]}
        for r in retired_rows
    ]

    return {"year": year, "title_changes": title_changes,
            "breakout_prospects": breakout[:5], "retirements": retirements}
