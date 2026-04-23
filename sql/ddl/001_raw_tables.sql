CREATE TABLE IF NOT EXISTS raw_sleep (
    raw_sleep_id BIGSERIAL PRIMARY KEY,
    calendar_date DATE,
    source_file TEXT NOT NULL UNIQUE,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_sleep_calendar_date ON raw_sleep (calendar_date);
CREATE INDEX IF NOT EXISTS idx_raw_sleep_payload_gin ON raw_sleep USING GIN (payload);

CREATE TABLE IF NOT EXISTS raw_daily_health (
    raw_daily_health_id BIGSERIAL PRIMARY KEY,
    calendar_date DATE,
    source_file TEXT NOT NULL UNIQUE,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_daily_health_calendar_date ON raw_daily_health (calendar_date);
CREATE INDEX IF NOT EXISTS idx_raw_daily_health_payload_gin ON raw_daily_health USING GIN (payload);

CREATE TABLE IF NOT EXISTS raw_activities (
    raw_activity_id BIGSERIAL PRIMARY KEY,
    calendar_date DATE,
    source_file TEXT NOT NULL UNIQUE,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_activities_calendar_date ON raw_activities (calendar_date);
CREATE INDEX IF NOT EXISTS idx_raw_activities_payload_gin ON raw_activities USING GIN (payload);

CREATE TABLE IF NOT EXISTS raw_hrv (
    raw_hrv_id BIGSERIAL PRIMARY KEY,
    calendar_date DATE,
    source_file TEXT NOT NULL UNIQUE,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_hrv_calendar_date ON raw_hrv (calendar_date);
CREATE INDEX IF NOT EXISTS idx_raw_hrv_payload_gin ON raw_hrv USING GIN (payload);
