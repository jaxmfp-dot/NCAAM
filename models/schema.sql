-- Per-save SQLite schema. Each save slot is its own .db file using this schema.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS game_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    save_name       TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    current_date    TEXT NOT NULL,   -- in-universe calendar date (ISO), advanced in Phase 4
    universe_mode   TEXT NOT NULL    -- 'generated' | 'imported' | 'mixed'
);

CREATE TABLE IF NOT EXISTS fighters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    name                TEXT NOT NULL,
    nickname            TEXT,
    dob                 TEXT NOT NULL,          -- ISO date, age computed at read time
    nationality         TEXT,
    hometown            TEXT,
    weight_class        TEXT NOT NULL,
    gender              TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    height_in           REAL,
    reach_in            REAL,
    stance              TEXT,                    -- Orthodox | Southpaw | Switch
    wins                INTEGER NOT NULL DEFAULT 0,
    losses              INTEGER NOT NULL DEFAULT 0,
    draws               INTEGER NOT NULL DEFAULT 0,
    no_contests         INTEGER NOT NULL DEFAULT 0,
    wins_ko             INTEGER NOT NULL DEFAULT 0,
    wins_sub            INTEGER NOT NULL DEFAULT 0,
    wins_dec            INTEGER NOT NULL DEFAULT 0,
    losses_ko           INTEGER NOT NULL DEFAULT 0,
    losses_sub          INTEGER NOT NULL DEFAULT 0,
    losses_dec          INTEGER NOT NULL DEFAULT 0,
    portrait_filename   TEXT,

    -- Striking
    punch_technique     INTEGER NOT NULL,
    kick_technique      INTEGER NOT NULL,
    knee_technique      INTEGER NOT NULL,
    elbow_technique     INTEGER NOT NULL,
    punch_power         INTEGER NOT NULL,
    kick_power          INTEGER NOT NULL,
    striking_defense    INTEGER NOT NULL,
    head_movement       INTEGER NOT NULL,
    chin                INTEGER NOT NULL,

    -- Grappling
    takedowns           INTEGER NOT NULL,
    takedown_defense    INTEGER NOT NULL,
    clinch_work         INTEGER NOT NULL,
    top_control         INTEGER NOT NULL,
    bottom_game         INTEGER NOT NULL,
    submissions         INTEGER NOT NULL,
    submission_defense  INTEGER NOT NULL,
    scrambling          INTEGER NOT NULL,

    -- Physical
    strength            INTEGER NOT NULL,
    speed               INTEGER NOT NULL,
    agility             INTEGER NOT NULL,
    cardio              INTEGER NOT NULL,
    recovery            INTEGER NOT NULL,
    toughness           INTEGER NOT NULL,
    injury_proneness    INTEGER NOT NULL,

    -- Mental
    heart               INTEGER NOT NULL,
    killer_instinct     INTEGER NOT NULL,
    fight_iq            INTEGER NOT NULL,
    composure           INTEGER NOT NULL,
    work_ethic          INTEGER NOT NULL,
    consistency         INTEGER NOT NULL,

    -- Career
    potential           INTEGER NOT NULL,
    momentum            INTEGER NOT NULL DEFAULT 0,
    prime_start_age     INTEGER NOT NULL,
    prime_end_age       INTEGER NOT NULL,
    popularity          INTEGER NOT NULL DEFAULT 20,
    contract_status     TEXT NOT NULL DEFAULT 'Signed',
    status               TEXT NOT NULL DEFAULT 'Active',
    archetype           TEXT,

    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fighters_weight_class ON fighters (weight_class);
CREATE INDEX IF NOT EXISTS idx_fighters_status ON fighters (status);
CREATE INDEX IF NOT EXISTS idx_fighters_name ON fighters (name);

-- =========================================================================
-- Booking (Phase 3)
-- =========================================================================

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    event_date      TEXT NOT NULL,          -- ISO date
    venue           TEXT,
    status          TEXT NOT NULL DEFAULT 'Scheduled',  -- Scheduled | Completed
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row per (division, interim/undisputed) belt. Created lazily the first
-- time a title fight is booked for that division; champion_id NULL = vacant.
CREATE TABLE IF NOT EXISTS titles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    weight_class    TEXT NOT NULL,
    gender          TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    is_interim      INTEGER NOT NULL DEFAULT 0,
    champion_id     INTEGER REFERENCES fighters(id),
    won_date        TEXT,
    defenses        INTEGER NOT NULL DEFAULT 0,
    UNIQUE(weight_class, gender, is_interim)
);

CREATE TABLE IF NOT EXISTS bouts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id                INTEGER NOT NULL REFERENCES events(id),
    bout_order              INTEGER NOT NULL,     -- ascending; highest = main event
    card_segment            TEXT NOT NULL DEFAULT 'main',  -- 'prelim' | 'main'

    fighter_a_id            INTEGER NOT NULL REFERENCES fighters(id),
    fighter_b_id            INTEGER NOT NULL REFERENCES fighters(id),
    weight_class            TEXT NOT NULL,
    gender                  TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    rounds                  INTEGER NOT NULL DEFAULT 3,

    is_title_fight          INTEGER NOT NULL DEFAULT 0,
    title_id                INTEGER REFERENCES titles(id),
    is_interim_title_fight  INTEGER NOT NULL DEFAULT 0,
    is_number_one_contender INTEGER NOT NULL DEFAULT 0,

    -- pre-fight opponent rank snapshot (0 = champion, 1-15 = ranked, NULL = unranked)
    -- a_faced_rank = the rank fighter_a's opponent (fighter_b) held going in, and vice versa
    a_faced_rank            INTEGER,
    b_faced_rank            INTEGER,

    status                  TEXT NOT NULL DEFAULT 'Scheduled',  -- Scheduled | Completed
    winner_id               INTEGER REFERENCES fighters(id),    -- NULL if draw
    method                  TEXT,        -- KO | TKO | SUB | DEC | DRAW
    method_detail           TEXT,
    result_round            INTEGER,
    result_time             TEXT,
    stats_json              TEXT,
    scorecards_json         TEXT,
    play_by_play_json       TEXT,

    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bouts_event ON bouts (event_id);
CREATE INDEX IF NOT EXISTS idx_bouts_fighter_a ON bouts (fighter_a_id);
CREATE INDEX IF NOT EXISTS idx_bouts_fighter_b ON bouts (fighter_b_id);
CREATE INDEX IF NOT EXISTS idx_titles_division ON titles (weight_class, gender);
