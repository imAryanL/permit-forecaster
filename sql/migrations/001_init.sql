CREATE TABLE permits (
    id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city  TEXT NOT NULL,
    permit_number TEXT NOT NULL,
    permit_type TEXT NOT NULL,
    work_category  TEXT,
    description   TEXT,
    cost  NUMERIC,
    applied_date DATE NOT NULL,
    issued_date DATE NOT NULL,
    wait_days  INTEGER GENERATED ALWAYS AS (issued_date - applied_date) STORED,
    status TEXT,
    UNIQUE (city, permit_number)
);

CREATE TABLE ingest_runs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city        TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_added  INTEGER,
    succeeded   BOOLEAN
);