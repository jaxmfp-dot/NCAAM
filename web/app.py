"""FastAPI backend: save-slot management, roster browsing, fighter profiles."""

import sys
from pathlib import Path
from typing import Literal, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import Body, FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, PlainTextResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import config  # noqa: E402
from engine import awards, booking, calendar, rankings, recap, reports, titles  # noqa: E402
from engine.fight.simulator import simulate_fight, simulate_many  # noqa: E402
from engine.generator import generate_universe  # noqa: E402
from engine.importer import import_fighters  # noqa: E402
from models import db, event as event_model, fighter as fighter_model  # noqa: E402

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


class CreateEventRequest(BaseModel):
    name: str
    event_date: str
    venue: Optional[str] = None


class BookBoutRequest(BaseModel):
    fighter_a_id: int
    fighter_b_id: int
    rounds: int = config.DEFAULT_ROUNDS
    card_segment: Literal["main", "prelim"] = "main"
    is_title_fight: bool = False
    is_interim_title_fight: bool = False
    is_number_one_contender: bool = False


class SimRequest(BaseModel):
    seed: Optional[int] = None


class AdvanceCalendarRequest(BaseModel):
    weeks: int = 1
    seed: Optional[int] = None


@app.get("/api/saves")
def api_list_saves():
    return db.list_saves()


@app.delete("/api/saves/{slot}")
def api_delete_save(slot: str):
    if not db.save_exists(slot):
        raise HTTPException(status_code=404, detail=f"Save slot '{slot}' not found")
    db.delete_save(slot)
    return {"deleted": slot}


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
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    streak_type: Optional[Literal["W", "L"]] = None,
    min_streak: int = 1,
    ranked_only: bool = False,
):
    conn = _get_conn(slot)
    try:
        fighters = fighter_model.list_fighters(
            conn, division=division, gender=gender, search=search, status=status, sort=sort,
            age_min=age_min, age_max=age_max,
        )

        streaks = event_model.compute_streaks(conn)
        for f in fighters:
            f["streak"] = streaks.get(f["id"], {"type": None, "count": 0})
        if streak_type:
            fighters = [f for f in fighters if f["streak"]["type"] == streak_type
                        and f["streak"]["count"] >= min_streak]

        if ranked_only and division and gender:
            rk = rankings.compute_rankings(conn, division, gender)
            ranked_ids = {c["fighter"]["id"] for c in rk["contenders"]}
            if rk["champion"]:
                ranked_ids.add(rk["champion"]["id"])
            if rk["interim_champion"]:
                ranked_ids.add(rk["interim_champion"]["id"])
            fighters = [f for f in fighters if f["id"] in ranked_ids]

        return fighters
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


@app.patch("/api/saves/{slot}/fighters/{fighter_id}")
def api_update_fighter(slot: str, fighter_id: int, updates: dict = Body(...)):
    conn = _get_conn(slot)
    try:
        if fighter_model.get_fighter(conn, fighter_id) is None:
            raise HTTPException(status_code=404, detail="Fighter not found")
        try:
            return fighter_model.update_fighter(conn, fighter_id, updates)
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e))
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


@app.get("/api/saves/{slot}/events")
def api_list_events(slot: str):
    conn = _get_conn(slot)
    try:
        return event_model.list_events(conn)
    finally:
        conn.close()


@app.post("/api/saves/{slot}/events")
def api_create_event(slot: str, req: CreateEventRequest):
    conn = _get_conn(slot)
    try:
        event_id = event_model.create_event(conn, req.name, req.event_date, req.venue)
        return event_model.get_event(conn, event_id)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/events/{event_id}")
def api_get_event(slot: str, event_id: int):
    conn = _get_conn(slot)
    try:
        ev = event_model.get_event(conn, event_id)
        if ev is None:
            raise HTTPException(status_code=404, detail="Event not found")
        ev["bouts"] = event_model.list_bouts(conn, event_id)
        return ev
    finally:
        conn.close()


@app.get("/api/saves/{slot}/events/{event_id}/export")
def api_export_event(slot: str, event_id: int):
    conn = _get_conn(slot)
    try:
        try:
            text = recap.export_event_text(conn, event_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return PlainTextResponse(text)
    finally:
        conn.close()


@app.post("/api/saves/{slot}/events/{event_id}/bouts")
def api_add_bout(slot: str, event_id: int, req: BookBoutRequest):
    conn = _get_conn(slot)
    try:
        if event_model.get_event(conn, event_id) is None:
            raise HTTPException(status_code=404, detail="Event not found")
        try:
            bout_id = booking.book_bout(
                conn, event_id, req.fighter_a_id, req.fighter_b_id, rounds=req.rounds,
                card_segment=req.card_segment, is_title_fight=req.is_title_fight,
                is_interim_title_fight=req.is_interim_title_fight,
                is_number_one_contender=req.is_number_one_contender,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return event_model.get_bout(conn, bout_id)
    finally:
        conn.close()


@app.delete("/api/saves/{slot}/events/{event_id}/bouts/{bout_id}")
def api_remove_bout(slot: str, event_id: int, bout_id: int):
    conn = _get_conn(slot)
    try:
        if not event_model.remove_bout(conn, bout_id):
            raise HTTPException(status_code=400, detail="Bout can't be removed (already completed, or not found)")
        return {"removed": True}
    finally:
        conn.close()


@app.post("/api/saves/{slot}/events/{event_id}/sim")
def api_sim_event(slot: str, event_id: int, req: SimRequest):
    conn = _get_conn(slot)
    try:
        if event_model.get_event(conn, event_id) is None:
            raise HTTPException(status_code=404, detail="Event not found")
        try:
            results = booking.sim_event(conn, event_id, seed=req.seed)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"results": results}
    finally:
        conn.close()


@app.post("/api/saves/{slot}/bouts/{bout_id}/sim")
def api_sim_bout(slot: str, bout_id: int, req: SimRequest):
    conn = _get_conn(slot)
    try:
        try:
            return booking.sim_bout(conn, bout_id, seed=req.seed)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/api/saves/{slot}/rankings/{weight_class}")
def api_rankings(slot: str, weight_class: str, gender: str = "M", as_of: Optional[str] = None):
    conn = _get_conn(slot)
    try:
        return rankings.compute_rankings(conn, weight_class, gender, as_of_date=as_of)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/titles")
def api_titles(slot: str):
    conn = _get_conn(slot)
    try:
        return titles.list_titles(conn)
    finally:
        conn.close()


@app.post("/api/saves/{slot}/titles/{title_id}/vacate")
def api_vacate_title(slot: str, title_id: int):
    conn = _get_conn(slot)
    try:
        titles.vacate_title(conn, title_id)
        return {"vacated": True}
    finally:
        conn.close()


@app.get("/api/saves/{slot}/fighters/{fighter_id}/history")
def api_fighter_history(slot: str, fighter_id: int):
    conn = _get_conn(slot)
    try:
        return event_model.fighter_history(conn, fighter_id)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/head-to-head")
def api_head_to_head(slot: str, a: int, b: int):
    conn = _get_conn(slot)
    try:
        return event_model.head_to_head(conn, a, b)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/calendar")
def api_get_calendar(slot: str):
    conn = _get_conn(slot)
    try:
        return db.get_game_state(conn)
    finally:
        conn.close()


@app.post("/api/saves/{slot}/calendar/advance")
def api_advance_calendar(slot: str, req: AdvanceCalendarRequest):
    if req.weeks < 1 or req.weeks > 520:
        raise HTTPException(status_code=400, detail="weeks must be between 1 and 520")
    conn = _get_conn(slot)
    try:
        return calendar.advance_weeks(conn, req.weeks, seed=req.seed)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/year-review/{year}")
def api_year_review(slot: str, year: int):
    conn = _get_conn(slot)
    try:
        return reports.year_in_review(conn, year)
    finally:
        conn.close()


@app.get("/api/saves/{slot}/awards/{year}")
def api_awards(slot: str, year: int):
    conn = _get_conn(slot)
    try:
        return awards.yearly_awards(conn, year)
    finally:
        conn.close()


# SPA static assets + index fallback (mounted last so /api routes take priority)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
