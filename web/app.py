"""FastAPI backend: save-slot management, roster browsing, fighter profiles."""

import sys
from pathlib import Path
from typing import Literal, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import config  # noqa: E402
from engine.fight.simulator import simulate_fight, simulate_many  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from engine.importer import import_fighters  # noqa: E402
from models import db, fighter as fighter_model  # noqa: E402

app = FastAPI(title="MMA Universe Simulator")

IMPORT_DIR = ROOT / config.IMPORT_DIR
IMPORT_PORTRAITS_DIR = ROOT / config.IMPORT_PORTRAITS_DIR
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _get_conn(slot: str):
    if not db.save_exists(slot):
        raise HTTPException(status_code=404, detail=f"Save slot '{slot}' not found")
    return db.get_connection(slot)


class CreateSaveRequest(BaseModel):
    name: str
    mode: Literal["generate", "import", "empty"] = "generate"
    seed: Optional[int] = None
    import_filename: Optional[str] = None


class FightTestRequest(BaseModel):
    fighter_a_id: int
    fighter_b_id: int
    rounds: int = config.DEFAULT_ROUNDS
    seed: Optional[int] = None


class FightBatchRequest(FightTestRequest):
    n: int = 1000


@app.get("/api/saves")
def api_list_saves():
    return db.list_saves()


@app.post("/api/saves")
def api_create_save(req: CreateSaveRequest):
    slot = db.slugify(req.name)
    if db.save_exists(slot):
        raise HTTPException(status_code=409, detail=f"A save named '{req.name}' already exists")

    conn = db.create_save(slot, req.name, universe_mode=req.mode)

    result = {"slot": slot}
    if req.mode == "generate":
        fighters = generate_universe(seed=req.seed)
        for f in fighters:
            fighter_model.insert_fighter(conn, f)
        conn.commit()
        result["fighters_created"] = len(fighters)
    elif req.mode == "import":
        source = (IMPORT_DIR / req.import_filename) if req.import_filename else None
        if source is None:
            candidates = list(IMPORT_DIR.glob("fighters.csv")) + list(IMPORT_DIR.glob("fighters.json"))
            source = candidates[0] if candidates else None
        if source is None or not source.is_file():
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"No fighters file found in {config.IMPORT_DIR} (expected fighters.csv or fighters.json)",
            )
        portraits_dest = db.PORTRAITS_DIR / slot
        summary = import_fighters(conn, source, IMPORT_PORTRAITS_DIR, portraits_dest, seed=req.seed)
        result.update(summary)

    conn.close()
    return result


@app.get("/api/saves/{slot}/divisions")
def api_divisions(slot: str):
    conn = _get_conn(slot)
    try:
        return fighter_model.list_divisions(conn)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/fighters")
def api_list_fighters(
    slot: str,
    division: Optional[str] = None,
    gender: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = "Active",
    sort: str = "name",
):
    conn = _get_conn(slot)
    try:
        return fighter_model.list_fighters(
            conn, division=division, gender=gender, search=search, status=status, sort=sort
        )
    finally:
        conn.close()


@app.get("/api/saves/{slot}/fighters/{fighter_id}")
def api_get_fighter(slot: str, fighter_id: int):
    conn = _get_conn(slot)
    try:
        f = fighter_model.get_fighter(conn, fighter_id)
        if f is None:
            raise HTTPException(status_code=404, detail="Fighter not found")
        return f
    finally:
        conn.close()


@app.get("/api/saves/{slot}/fighters/{fighter_id}/portrait")
def api_fighter_portrait(slot: str, fighter_id: int):
    conn = _get_conn(slot)
    try:
        f = fighter_model.get_fighter(conn, fighter_id)
    finally:
        conn.close()
    if f is None or not f.get("portrait_filename"):
        raise HTTPException(status_code=404, detail="No portrait")
    path = db.PORTRAITS_DIR / slot / f["portrait_filename"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Portrait file missing on disk")
    return FileResponse(path)


def _fetch_pair(conn, fighter_a_id: int, fighter_b_id: int) -> tuple[dict, dict]:
    a = fighter_model.get_fighter(conn, fighter_a_id)
    b = fighter_model.get_fighter(conn, fighter_b_id)
    if a is None or b is None:
        missing = fighter_a_id if a is None else fighter_b_id
        raise HTTPException(status_code=404, detail=f"Fighter {missing} not found")
    return a, b


@app.post("/api/saves/{slot}/fight-test")
def api_fight_test(slot: str, req: FightTestRequest):
    conn = _get_conn(slot)
    try:
        a, b = _fetch_pair(conn, req.fighter_a_id, req.fighter_b_id)
    finally:
        conn.close()
    return simulate_fight(a, b, rounds=req.rounds, seed=req.seed)


@app.post("/api/saves/{slot}/fight-test/batch")
def api_fight_test_batch(slot: str, req: FightBatchRequest):
    if req.n < 1 or req.n > 5000:
        raise HTTPException(status_code=400, detail="n must be between 1 and 5000")
    conn = _get_conn(slot)
    try:
        a, b = _fetch_pair(conn, req.fighter_a_id, req.fighter_b_id)
    finally:
        conn.close()
    return simulate_many(a, b, n=req.n, rounds=req.rounds, seed=req.seed)


# SPA static assets + index fallback (mounted last so /api routes take priority)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
