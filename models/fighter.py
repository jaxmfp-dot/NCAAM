"""Fighter data access: row <-> dict helpers and simple queries against a save DB."""

import sqlite3
from datetime import date, datetime

import config

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
    "potential", "physical_gift", "momentum", "prime_start_age", "prime_end_age", "popularity",
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
    + ["potential", "physical_gift", "momentum", "prime_start_age", "prime_end_age", "popularity",
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


_VALID_WEIGHT_CLASSES = {d["key"] for d in config.WEIGHT_CLASSES}
_RECORD_INT_FIELDS = set(RECORD_FIELDS) | {"prime_start_age", "prime_end_age"}


def set_rank_seed(conn: sqlite3.Connection, fighter_id: int, rank: int | None, as_of_date: str):
    """Gives a fighter a starting-credential rank (1-15) with no sim fight history yet;
    see engine/rankings.py for how it decays. Pass rank=None to clear a seed."""
    if rank is not None and not (1 <= rank <= 15):
        raise ValueError("rank must be between 1 and 15 (or None to clear)")
    conn.execute(
        "UPDATE fighters SET manual_rank_seed = ?, manual_rank_seed_date = ? WHERE id = ?",
        (rank, as_of_date if rank is not None else None, fighter_id),
    )
    conn.commit()


def update_fighter(conn: sqlite3.Connection, fighter_id: int, updates: dict) -> dict:
    """In-game editor: validates and clamps a partial update, editable-field whitelist
    is INSERTABLE_FIELDS (everything the importer/generator can set)."""
    unknown = set(updates) - set(INSERTABLE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown or non-editable field(s): {', '.join(sorted(unknown))}")

    clean = {}
    for key, value in updates.items():
        if key in SKILL_ATTRS or key in ("potential", "physical_gift"):
            clean[key] = max(config.ATTR_MIN, min(config.ATTR_MAX, int(value)))
        elif key == "momentum":
            clean[key] = max(config.MOMENTUM_MIN, min(config.MOMENTUM_MAX, int(value)))
        elif key == "popularity":
            clean[key] = max(1, min(99, int(value)))
        elif key == "dob":
            datetime.strptime(value, "%Y-%m-%d")  # raises ValueError if unparseable
            clean[key] = value
        elif key == "gender":
            if value not in ("M", "F"):
                raise ValueError("gender must be 'M' or 'F'")
            clean[key] = value
        elif key == "weight_class":
            if value not in _VALID_WEIGHT_CLASSES:
                raise ValueError(f"Unknown weight_class: {value!r}")
            clean[key] = value
        elif key in _RECORD_INT_FIELDS:
            clean[key] = int(value)
        else:
            clean[key] = value

    if clean:
        set_clause = ", ".join(f"{k} = ?" for k in clean)
        conn.execute(f"UPDATE fighters SET {set_clause} WHERE id = ?", (*clean.values(), fighter_id))
        conn.commit()
    return get_fighter(conn, fighter_id)


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
    age_min: int | None = None,
    age_max: int | None = None,
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
    fighters = [row_to_dict(r) for r in rows]
    if age_min is not None:
        fighters = [f for f in fighters if f["age"] >= age_min]
    if age_max is not None:
        fighters = [f for f in fighters if f["age"] <= age_max]
    return fighters


def get_fighter(conn: sqlite3.Connection, fighter_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM fighters WHERE id = ?", (fighter_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_divisions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT weight_class, gender, COUNT(*) AS count FROM fighters "
        "WHERE status = 'Active' GROUP BY weight_class, gender ORDER BY gender, weight_class"
    ).fetchall()
    return [dict(r) for r in rows]
