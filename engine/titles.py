"""Belt/title logic: lazy creation, champion lookup, vacancy, defense/change resolution."""

import sqlite3


def get_title(conn: sqlite3.Connection, weight_class: str, gender: str, is_interim: bool = False) -> dict | None:
    row = conn.execute(
        "SELECT * FROM titles WHERE weight_class = ? AND gender = ? AND is_interim = ?",
        (weight_class, gender, int(is_interim)),
    ).fetchone()
    return dict(row) if row else None


def ensure_title(conn: sqlite3.Connection, weight_class: str, gender: str, is_interim: bool = False) -> int:
    """Returns the title's id, creating a vacant belt for this division if none exists yet."""
    existing = get_title(conn, weight_class, gender, is_interim)
    if existing:
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO titles (weight_class, gender, is_interim) VALUES (?, ?, ?)",
        (weight_class, gender, int(is_interim)),
    )
    conn.commit()
    return cur.lastrowid


def get_champion(conn: sqlite3.Connection, weight_class: str, gender: str, is_interim: bool = False) -> dict | None:
    title = get_title(conn, weight_class, gender, is_interim)
    if title is None or title["champion_id"] is None:
        return None
    row = conn.execute("SELECT * FROM fighters WHERE id = ?", (title["champion_id"],)).fetchone()
    return dict(row) if row else None


def list_titles(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.*, f.name AS champion_name FROM titles t "
        "LEFT JOIN fighters f ON f.id = t.champion_id "
        "ORDER BY t.gender, t.weight_class, t.is_interim"
    ).fetchall()
    return [dict(r) for r in rows]


def vacate_title(conn: sqlite3.Connection, title_id: int):
    conn.execute("UPDATE titles SET champion_id = NULL, won_date = NULL, defenses = 0 WHERE id = ?", (title_id,))
    conn.commit()


def resolve_title_bout(conn: sqlite3.Connection, title_id: int, winner_id: int, event_date: str) -> dict:
    """Applies a title fight's result. Returns {'title_changed': bool, 'was_vacant': bool}."""
    title = conn.execute("SELECT * FROM titles WHERE id = ?", (title_id,)).fetchone()
    was_vacant = title["champion_id"] is None
    title_changed = was_vacant or title["champion_id"] != winner_id

    if title_changed:
        conn.execute(
            "UPDATE titles SET champion_id = ?, won_date = ?, defenses = 0 WHERE id = ?",
            (winner_id, event_date, title_id),
        )
    else:
        conn.execute("UPDATE titles SET defenses = defenses + 1 WHERE id = ?", (title_id,))
    conn.commit()
    return {"title_changed": title_changed, "was_vacant": was_vacant}
