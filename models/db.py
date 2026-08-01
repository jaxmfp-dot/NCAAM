"""Save-slot connection management. Each save is one SQLite file under SAVES_DIR."""

import re
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
SAVES_DIR = ROOT / config.SAVES_DIR
PORTRAITS_DIR = ROOT / config.PORTRAITS_DIR
SCHEMA_PATH = ROOT / config.SCHEMA_PATH

_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Save name must contain at least one alphanumeric character")
    return slug


def save_path(slot: str) -> Path:
    return SAVES_DIR / f"{slot}.db"


def save_exists(slot: str) -> bool:
    return save_path(slot).is_file()


def get_connection(slot: str) -> sqlite3.Connection:
    if not save_exists(slot):
        raise FileNotFoundError(f"No save slot named '{slot}'")
    conn = sqlite3.connect(save_path(slot))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_save(slot: str, save_name: str, universe_mode: str, start_date: str | None = None) -> sqlite3.Connection:
    """Create a fresh save DB file, apply schema, and seed game_state. Fails if it already exists."""
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    path = save_path(slot)
    if path.exists():
        raise FileExistsError(f"Save slot '{slot}' already exists")

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute(
        "INSERT INTO game_state (id, save_name, current_date, universe_mode) VALUES (1, ?, ?, ?)",
        (save_name, start_date or date.today().isoformat(), universe_mode),
    )
    conn.commit()

    (PORTRAITS_DIR / slot).mkdir(parents=True, exist_ok=True)
    return conn


def delete_save(slot: str):
    """Removes a save's database file and its portrait folder. Irreversible."""
    path = save_path(slot)
    if path.exists():
        path.unlink()
    portraits_dir = PORTRAITS_DIR / slot
    if portraits_dir.is_dir():
        shutil.rmtree(portraits_dir)


def get_game_state(conn: sqlite3.Connection) -> dict:
    return dict(conn.execute("SELECT * FROM game_state WHERE id = 1").fetchone())


def set_current_date(conn: sqlite3.Connection, new_date: str):
    conn.execute("UPDATE game_state SET current_date = ? WHERE id = 1", (new_date,))


def list_saves() -> list[dict]:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    saves = []
    for path in sorted(SAVES_DIR.glob("*.db")):
        slot = path.stem
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            state = conn.execute("SELECT * FROM game_state WHERE id = 1").fetchone()
            fighter_count = conn.execute("SELECT COUNT(*) AS c FROM fighters").fetchone()["c"]
            conn.close()
        except sqlite3.Error:
            continue
        if state is None:
            continue
        saves.append({
            "slot": slot,
            "name": state["save_name"],
            "created_at": state["created_at"],
            "current_date": state["current_date"],
            "universe_mode": state["universe_mode"],
            "fighter_count": fighter_count,
        })
    return saves
