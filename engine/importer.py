"""Import fighters from a user-supplied CSV/JSON file plus a portraits folder.

Column names are matched case-insensitively and normalized (spaces/dashes ->
underscores, a few common aliases). Any attribute the file doesn't provide is
filled with a sensible random default rather than rejecting the row, so a
partial roster (e.g. just names + records) still imports.
"""

import csv
import json
import random
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import config
from models.fighter import GRAPPLING_ATTRS, MENTAL_ATTRS, PHYSICAL_ATTRS, STRIKING_ATTRS

SKILL_ATTRS = STRIKING_ATTRS + GRAPPLING_ATTRS + PHYSICAL_ATTRS + MENTAL_ATTRS

ALIASES = {
    "division": "weight_class", "weightclass": "weight_class", "weight_class_name": "weight_class",
    "sex": "gender",
    "birthdate": "dob", "birth_date": "dob", "date_of_birth": "dob",
    "portrait": "portrait_filename", "image": "portrait_filename", "photo": "portrait_filename",
    "picture": "portrait_filename",
    "height": "height_in", "height_inches": "height_in",
    "reach": "reach_in", "reach_inches": "reach_in",
    "record_wins": "wins", "record_losses": "losses", "record_draws": "draws",
}

VALID_DIVISIONS = {d["key"]: d["gender"] for d in config.WEIGHT_CLASSES}

PORTRAIT_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]


class ImportError_(Exception):
    pass


def _normalize_key(key: str) -> str:
    key = key.strip().lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(key, key)


def _normalize_record(raw: dict) -> dict:
    return {_normalize_key(k): v for k, v in raw.items() if k is not None and str(k).strip() != ""}


def parse_fighters_file(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        rows = data["fighters"] if isinstance(data, dict) and "fighters" in data else data
        if not isinstance(rows, list):
            raise ImportError_("JSON file must contain a list of fighters (or {\"fighters\": [...]})")
        return [_normalize_record(row) for row in rows]
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [_normalize_record(row) for row in reader]
    raise ImportError_(f"Unsupported file type: {path.suffix}")


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def find_portrait(record: dict, portraits_dir: Path) -> str | None:
    explicit = record.get("portrait_filename")
    if explicit and (portraits_dir / str(explicit)).is_file():
        return str(explicit)

    if not portraits_dir.is_dir():
        return None
    name_slug = _slug(str(record.get("name", "")))
    if not name_slug:
        return None
    for f in portraits_dir.iterdir():
        if f.suffix.lower() in PORTRAIT_EXTENSIONS and _slug(f.stem) == name_slug:
            return f.name
    return None


def _to_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_attr(value) -> int:
    return max(config.ATTR_MIN, min(config.ATTR_MAX, round(value)))


def _resolve_dob(record: dict, as_of: date) -> str:
    dob = record.get("dob")
    if dob:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(dob).strip(), fmt).date().isoformat()
            except ValueError:
                continue
        raise ImportError_(f"Unrecognized dob format: {dob!r}")
    age = _to_float(record.get("age"))
    if age is not None:
        return date(int(as_of.year - age), 1, 1).isoformat()
    raise ImportError_("Row is missing both 'dob' and 'age'")


def _resolve_weight_class(record: dict) -> tuple[str, str]:
    wc = record.get("weight_class")
    if not wc or wc not in VALID_DIVISIONS:
        raise ImportError_(f"Unknown or missing weight_class: {wc!r}")
    gender = record.get("gender")
    if gender:
        gender = str(gender).strip().upper()[0]
    else:
        gender = VALID_DIVISIONS[wc]
    return wc, gender


def normalize_fighter(record: dict, rng: random.Random, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    if not record.get("name"):
        raise ImportError_("Row is missing 'name'")

    weight_class, gender = _resolve_weight_class(record)
    dob = _resolve_dob(record, as_of)

    fighter = {
        "name": str(record["name"]).strip(),
        "nickname": record.get("nickname") or None,
        "dob": dob,
        "nationality": record.get("nationality") or None,
        "hometown": record.get("hometown") or None,
        "weight_class": weight_class,
        "gender": gender,
        "height_in": _to_float(record.get("height_in")),
        "reach_in": _to_float(record.get("reach_in")),
        "stance": record.get("stance") or None,
        "portrait_filename": record.get("portrait_filename") or None,
        "contract_status": record.get("contract_status") or "Signed",
        "promotion": record.get("promotion") or "UFC",
        "status": record.get("status") or "Active",
        "archetype": record.get("archetype") or None,
    }

    for field in ("wins", "losses", "draws", "no_contests",
                  "wins_ko", "wins_sub", "wins_dec", "losses_ko", "losses_sub", "losses_dec"):
        fighter[field] = int(_to_float(record.get(field), 0))

    skill_values = {}
    for attr in SKILL_ATTRS:
        raw = _to_float(record.get(attr))
        skill_values[attr] = _clamp_attr(raw) if raw is not None else _clamp_attr(rng.gauss(50, 10))
    fighter.update(skill_values)

    avg_skill = sum(skill_values.values()) / len(skill_values)
    potential = _to_float(record.get("potential"))
    fighter["potential"] = (_clamp_attr(potential) if potential is not None
                             else _clamp_attr(max(avg_skill, avg_skill + rng.randint(5, 20))))
    physical_gift = _to_float(record.get("physical_gift"))
    fighter["physical_gift"] = (_clamp_attr(physical_gift) if physical_gift is not None
                                 else _clamp_attr(fighter["potential"] + rng.gauss(0, config.PHYSICAL_GIFT_NOISE_STDEV)))
    fighter["momentum"] = int(_to_float(record.get("momentum"), 0))
    fighter["prime_start_age"] = int(_to_float(record.get("prime_start_age"),
                                                rng.randint(config.PRIME_START_MIN, config.PRIME_START_MAX)))
    default_prime_end = fighter["prime_start_age"] + rng.randint(config.PRIME_LENGTH_MIN, config.PRIME_LENGTH_MAX)
    fighter["prime_end_age"] = int(_to_float(record.get("prime_end_age"), default_prime_end))
    fighter["popularity"] = _clamp_attr(_to_float(record.get("popularity"), config.POPULARITY_BASE))

    return fighter


def import_fighters(conn, source_path: Path, portraits_src_dir: Path | None,
                     portraits_dest_dir: Path, seed: int | None = None) -> dict:
    from models.fighter import insert_fighter

    rng = random.Random(seed)
    raw_rows = parse_fighters_file(source_path)

    imported = 0
    errors = []
    portraits_dest_dir.mkdir(parents=True, exist_ok=True)

    for i, raw in enumerate(raw_rows):
        try:
            fighter = normalize_fighter(raw, rng)
            if portraits_src_dir:
                filename = find_portrait(raw, portraits_src_dir)
                if filename:
                    shutil.copy2(portraits_src_dir / filename, portraits_dest_dir / filename)
                    fighter["portrait_filename"] = filename
            insert_fighter(conn, fighter)
            imported += 1
        except ImportError_ as e:
            errors.append({"row": i, "name": raw.get("name"), "error": str(e)})

    conn.commit()
    return {"imported": imported, "skipped": len(errors), "errors": errors}
