"""Event/bout data access: booking a card, recording results, fight history."""

import json
import sqlite3


def create_event(conn: sqlite3.Connection, name: str, event_date: str, venue: str | None) -> int:
    cur = conn.execute(
        "INSERT INTO events (name, event_date, venue) VALUES (?, ?, ?)",
        (name, event_date, venue),
    )
    conn.commit()
    return cur.lastrowid


def list_events(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT e.*, COUNT(b.id) AS bout_count, "
        "SUM(CASE WHEN b.status = 'Completed' THEN 1 ELSE 0 END) AS bouts_completed "
        "FROM events e LEFT JOIN bouts b ON b.event_id = e.id "
        "GROUP BY e.id ORDER BY e.event_date DESC, e.id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_event(conn: sqlite3.Connection, event_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def _bout_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("stats_json", "scorecards_json", "play_by_play_json"):
        raw = d.pop(key, None)
        target = key.replace("_json", "")
        d[target] = json.loads(raw) if raw else None
    return d


_BOUT_COLUMNS = """
    SELECT b.*,
           fa.name AS fighter_a_name, fa.wins AS fighter_a_wins, fa.losses AS fighter_a_losses,
           fa.draws AS fighter_a_draws, fa.no_contests AS fighter_a_no_contests,
           fb.name AS fighter_b_name, fb.wins AS fighter_b_wins, fb.losses AS fighter_b_losses,
           fb.draws AS fighter_b_draws, fb.no_contests AS fighter_b_no_contests
"""
_BOUT_FROM = """
    FROM bouts b
    JOIN fighters fa ON fa.id = b.fighter_a_id
    JOIN fighters fb ON fb.id = b.fighter_b_id
"""
_BOUT_SELECT = _BOUT_COLUMNS + _BOUT_FROM


def list_bouts(conn: sqlite3.Connection, event_id: int) -> list[dict]:
    rows = conn.execute(
        _BOUT_SELECT + " WHERE b.event_id = ? ORDER BY b.card_segment DESC, b.bout_order ASC",
        (event_id,),
    ).fetchall()
    return [_bout_row_to_dict(r) for r in rows]


def get_bout(conn: sqlite3.Connection, bout_id: int) -> dict | None:
    row = conn.execute(_BOUT_SELECT + " WHERE b.id = ?", (bout_id,)).fetchone()
    return _bout_row_to_dict(row) if row else None


def add_bout(conn: sqlite3.Connection, event_id: int, fighter_a_id: int, fighter_b_id: int,
             weight_class: str, gender: str, rounds: int = 3, card_segment: str = "main",
             is_title_fight: bool = False, title_id: int | None = None,
             is_interim_title_fight: bool = False, is_number_one_contender: bool = False) -> int:
    next_order = conn.execute(
        "SELECT COALESCE(MAX(bout_order), 0) + 1 AS n FROM bouts WHERE event_id = ?", (event_id,)
    ).fetchone()["n"]
    cur = conn.execute(
        "INSERT INTO bouts (event_id, bout_order, card_segment, fighter_a_id, fighter_b_id, "
        "weight_class, gender, rounds, is_title_fight, title_id, is_interim_title_fight, "
        "is_number_one_contender) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, next_order, card_segment, fighter_a_id, fighter_b_id, weight_class, gender,
         rounds, int(is_title_fight), title_id, int(is_interim_title_fight), int(is_number_one_contender)),
    )
    conn.commit()
    return cur.lastrowid


def remove_bout(conn: sqlite3.Connection, bout_id: int) -> bool:
    row = conn.execute("SELECT status FROM bouts WHERE id = ?", (bout_id,)).fetchone()
    if row is None or row["status"] != "Scheduled":
        return False
    conn.execute("DELETE FROM bouts WHERE id = ?", (bout_id,))
    conn.commit()
    return True


def record_bout_result(conn: sqlite3.Connection, bout_id: int, result: dict,
                        a_faced_rank: int | None, b_faced_rank: int | None):
    conn.execute(
        "UPDATE bouts SET status = 'Completed', winner_id = ?, method = ?, method_detail = ?, "
        "result_round = ?, result_time = ?, stats_json = ?, scorecards_json = ?, "
        "play_by_play_json = ?, a_faced_rank = ?, b_faced_rank = ? WHERE id = ?",
        (
            result.get("winner_fighter_id"), result["method"], result["method_detail"],
            result["round"], result["time"],
            json.dumps({"fighter_a": result["fighter_a"], "fighter_b": result["fighter_b"]}),
            json.dumps(result["scorecards"]), json.dumps(result["play_by_play"]),
            a_faced_rank, b_faced_rank, bout_id,
        ),
    )
    conn.commit()


def set_title_change(conn: sqlite3.Connection, bout_id: int, changed: bool):
    conn.execute("UPDATE bouts SET title_change = ? WHERE id = ?", (int(changed), bout_id))
    conn.commit()


def refresh_event_status(conn: sqlite3.Connection, event_id: int):
    row = conn.execute(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS done "
        "FROM bouts WHERE event_id = ?", (event_id,)
    ).fetchone()
    status = "Completed" if row["total"] > 0 and row["total"] == row["done"] else "Scheduled"
    conn.execute("UPDATE events SET status = ? WHERE id = ?", (status, event_id))
    conn.commit()


def fighter_history(conn: sqlite3.Connection, fighter_id: int) -> list[dict]:
    rows = conn.execute(
        _BOUT_COLUMNS + ", e.name AS event_name, e.event_date AS event_date "
        + _BOUT_FROM
        + "JOIN events e ON e.id = b.event_id "
          "WHERE (b.fighter_a_id = ? OR b.fighter_b_id = ?) AND b.status = 'Completed' "
          "ORDER BY e.event_date DESC, b.bout_order DESC",
        (fighter_id, fighter_id),
    ).fetchall()
    out = []
    for row in rows:
        d = _bout_row_to_dict(row)
        is_a = d["fighter_a_id"] == fighter_id
        opponent_id = d["fighter_b_id"] if is_a else d["fighter_a_id"]
        opponent_name = d["fighter_b_name"] if is_a else d["fighter_a_name"]
        if d["winner_id"] is None:
            outcome = "Draw"
        elif d["winner_id"] == fighter_id:
            outcome = "Win"
        else:
            outcome = "Loss"
        d["opponent_id"] = opponent_id
        d["opponent_name"] = opponent_name
        d["outcome"] = outcome
        out.append(d)
    return out


def compute_streaks(conn: sqlite3.Connection) -> dict[int, dict]:
    """Current win/loss streak per fighter, e.g. {fighter_id: {'type': 'W', 'count': 3}}.
    A draw or no fights on record resets/omits the streak. Single pass over all completed
    bouts in chronological order -- O(bouts), not O(fighters * bouts)."""
    rows = conn.execute(
        "SELECT b.fighter_a_id, b.fighter_b_id, b.winner_id FROM bouts b "
        "JOIN events e ON e.id = b.event_id "
        "WHERE b.status = 'Completed' ORDER BY e.event_date ASC, b.bout_order ASC"
    ).fetchall()

    sequences: dict[int, list[str]] = {}
    for row in rows:
        a, b, winner = row["fighter_a_id"], row["fighter_b_id"], row["winner_id"]
        for fighter_id, outcome in (
            (a, "W" if winner == a else ("D" if winner is None else "L")),
            (b, "W" if winner == b else ("D" if winner is None else "L")),
        ):
            sequences.setdefault(fighter_id, []).append(outcome)

    streaks = {}
    for fighter_id, seq in sequences.items():
        last = seq[-1]
        if last == "D":
            streaks[fighter_id] = {"type": None, "count": 0}
            continue
        count = 0
        for outcome in reversed(seq):
            if outcome != last:
                break
            count += 1
        streaks[fighter_id] = {"type": last, "count": count}
    return streaks


def bouts_in_range(conn: sqlite3.Connection, start_date: str, end_date: str) -> list[dict]:
    rows = conn.execute(
        _BOUT_COLUMNS + ", e.name AS event_name, e.event_date AS event_date "
        + _BOUT_FROM
        + "JOIN events e ON e.id = b.event_id "
          "WHERE b.status = 'Completed' AND e.event_date BETWEEN ? AND ? "
          "ORDER BY e.event_date ASC, b.bout_order ASC",
        (start_date, end_date),
    ).fetchall()
    return [_bout_row_to_dict(r) for r in rows]


def results_tally_in_range(conn: sqlite3.Connection, start_date: str, end_date: str) -> tuple[dict, dict]:
    """Returns (wins_by_fighter_id, losses_by_fighter_id) counting only decided bouts."""
    wins, losses = {}, {}
    for bout in bouts_in_range(conn, start_date, end_date):
        winner = bout["winner_id"]
        if winner is None:
            continue
        loser = bout["fighter_b_id"] if winner == bout["fighter_a_id"] else bout["fighter_a_id"]
        wins[winner] = wins.get(winner, 0) + 1
        losses[loser] = losses.get(loser, 0) + 1
    return wins, losses


def head_to_head(conn: sqlite3.Connection, fighter_a_id: int, fighter_b_id: int) -> dict:
    rows = conn.execute(
        _BOUT_COLUMNS + ", e.name AS event_name, e.event_date AS event_date "
        + _BOUT_FROM
        + "JOIN events e ON e.id = b.event_id "
          "WHERE b.status = 'Completed' AND "
          "((b.fighter_a_id = ? AND b.fighter_b_id = ?) OR (b.fighter_a_id = ? AND b.fighter_b_id = ?)) "
          "ORDER BY e.event_date ASC",
        (fighter_a_id, fighter_b_id, fighter_b_id, fighter_a_id),
    ).fetchall()
    bouts = [_bout_row_to_dict(r) for r in rows]
    wins_a = sum(1 for b in bouts if b["winner_id"] == fighter_a_id)
    wins_b = sum(1 for b in bouts if b["winner_id"] == fighter_b_id)
    draws = sum(1 for b in bouts if b["winner_id"] is None)
    return {"wins_a": wins_a, "wins_b": wins_b, "draws": draws, "bouts": bouts}
