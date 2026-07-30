"""Fighter data access: row <-> dict helpers and simple queries against a save DB."""

import sqlite3
from datetime import date, datetime

STRIKING_ATTRS = [
    "punch_technique", "kick_technique", "knee_technique", "elbow_technique",
    "punch_power", "kick_power", "striking_defense", "head_movement", "chin",
]
GRAPPLING_ATTRS = [
    "takedowns", "takedown_defense", "clinch_work", "top_control", "bottom_game",
    "submissions", "submission_defense", "scrambling",
]
PHYSICAL_ATTRS = [
    "strength", "speed", "agility", "cardio", "recovery", "toughness", "injury_proneness",
]
MENTAL_ATTRS = [
    "heart", "killer_instinct", "fight_iq", "composure", "work_ethic", "consistency",
]
CAREER_ATTRS = [
    "potential", "momentum", "prime_start_age", "prime_end_age", "popularity",
    "contract_status", "status", "archetype",
]

ATTRIBUTE_GROUPS = {
    "striking": STRIKING_ATTRS,
    "grappling": GRAPPLING_ATTRS,
    "physical": PHYSICAL_ATTRS,
    "mental": MENTAL_ATTRS,
}

# numeric skill attributes only (0-100 scale), used by the generator/importer/fight engine
SKILL_ATTRS = STRIKING_ATTRS + GRAPPLING_ATTRS + PHYSICAL_ATTRS + MENTAL_ATTRS

IDENTITY_FIELDS = [
    "name", "nickname", "dob", "nationality", "hometown", "weight_class", "gender",
    "height_in", "reach_in", "stance", "portrait_filename",
]
RECORD_FIELDS = [
    "wins", "losses", "draws", "no_contests",
    "wins_ko", "wins_sub", "wins_dec", "losses_ko", "losses_sub", "losses_dec",
]

INSERTABLE_FIELDS = (
    IDENTITY_FIELDS + RECORD_FIELDS + SKILL_ATTRS
    + ["potential", "momentum", "prime_start_age", "prime_end_age", "popularity",
       "contract_status", "status", "archetype"]
)


def compute_age(dob_str: str, as_of: date | None = None) -> int:
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    as_of = as_of or date.today()
    years = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        years -= 1
    return years


def record_string(row: dict) -> str:
    parts = f"{row['wins']}-{row['losses']}-{row['draws']}"
    if row.get("no_contests"):
        parts += f" ({row['no_contests']} NC)"
    return parts


def insert_fighter(conn: sqlite3.Connection, data: dict) -> int:
    missing = [f for f in INSERTABLE_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Fighter row missing fields: {missing}")
    columns = INSERTABLE_FIELDS
    placeholders = ", ".join("?" for _ in columns)
    values = [data[c] for c in columns]
    cur = conn.execute(
        f"INSERT INTO fighters ({', '.join(columns)}) VALUES ({placeholders})", values
    )
    return cur.lastrowid


def row_to_dict(row: sqlite3.Row, as_of: date | None = None) -> dict:
    d = dict(row)
    d["age"] = compute_age(d["dob"], as_of)
    d["record"] = record_string(d)
    return d


def list_fighters(
    conn: sqlite3.Connection,
    division: str | None = None,
    gender: str | None = None,
    search: str | None = None,
    status: str | None = "Active",
    sort: str = "name",
) -> list[dict]:
    query = "SELECT * FROM fighters WHERE 1=1"
    params: list = []
    if division:
        query += " AND weight_class = ?"
        params.append(division)
    if gender:
        query += " AND gender = ?"
        params.append(gender)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR nickname LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    sort_columns = {
        "name": "name COLLATE NOCASE ASC",
        "wins": "wins DESC",
        "age": "dob DESC",
        "popularity": "popularity DESC",
    }
    query += f" ORDER BY {sort_columns.get(sort, sort_columns['name'])}"

    rows = conn.execute(query, params).fetchall()
    return [row_to_dict(r) for r in rows]


def get_fighter(conn: sqlite3.Connection, fighter_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM fighters WHERE id = ?", (fighter_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_divisions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT weight_class, gender, COUNT(*) AS count FROM fighters "
        "WHERE status = 'Active' GROUP BY weight_class, gender ORDER BY gender, weight_class"
    ).fetchall()
    return [dict(r) for r in rows]
