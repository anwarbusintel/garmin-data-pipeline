# Garmin Data Pipeline

Garmin-only sleep analytics proof of concept built with Python, PostgreSQL, SQL views, and Streamlit.

The pipeline:

1. extracts Garmin data with Python,
2. stores raw API responses as JSON,
3. loads raw JSON into PostgreSQL,
4. builds staging and mart views with SQL,
5. serves a dashboard from `mart_sleep_correlates_daily`.

## Current Status

The implemented workflow now supports:

- Garmin login and extraction using your own account
- raw JSON persistence under `data/raw/`
- raw-table loading into PostgreSQL
- staging views for sleep, daily health, activities, and HRV
- an analysis-ready mart called `mart_sleep_correlates_daily`
- a working Streamlit dashboard backed by the mart

## Stack

- Python 3.14
- native PostgreSQL 17
- `garminconnect`
- `psycopg`
- plain SQL views
- Streamlit

## Project Layout

```text
garmin_data_pipeline/
├── app/
│   ├── extract/
│   ├── load/
│   ├── transform/
│   ├── utils/
│   └── main.py
├── dashboards/
│   └── streamlit_app.py
├── data/
│   └── raw/
├── sql/
│   ├── ddl/
│   ├── staging/
│   └── marts/
├── .env.example
├── README.md
└── requirements.txt
```

## Environment Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your Garmin and PostgreSQL credentials.

Required settings:

- `GARMIN_EMAIL`
- `GARMIN_PASSWORD`
- `GARMIN_MFA_CODE`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Important notes:

- Leave `GARMIN_DISABLE_ENV_PROXY=true` if your shell or machine sets proxy environment variables.
- If Garmin MFA is enabled, refresh `GARMIN_MFA_CODE` before running login or extraction commands.
- This project is currently documented for native PostgreSQL. `docker-compose.yml` exists, but the validated workflow in this repo uses native Postgres.

## PostgreSQL Setup

Create the raw tables:

```powershell
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/ddl/001_raw_tables.sql
```

If you want to clear previously loaded raw rows before a backfill:

```powershell
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/ddl/002_truncate_raw_tables.sql
```

## CLI Commands

The main entry point is `app.main`.

Available commands:

- `bootstrap`
- `login-test`
- `extract-recent`
- `extract-range`
- `load-raw`
- `run-sql`

### Test Garmin Login

```powershell
& .\.venv\Scripts\python.exe -m app.main login-test
```

### Extract Recent Data

```powershell
& .\.venv\Scripts\python.exe -m app.main extract-recent --days 7
```

Skip HRV if needed:

```powershell
& .\.venv\Scripts\python.exe -m app.main extract-recent --days 7 --skip-hrv
```

### Extract a Specific Date Range

```powershell
& .\.venv\Scripts\python.exe -m app.main extract-range --start-date 2025-03-01 --end-date 2025-06-30
```

Large historical pulls are safer month by month:

```powershell
& .\.venv\Scripts\python.exe -m app.main extract-range --start-date 2025-03-01 --end-date 2025-03-31
& .\.venv\Scripts\python.exe -m app.main extract-range --start-date 2025-04-01 --end-date 2025-04-30
& .\.venv\Scripts\python.exe -m app.main extract-range --start-date 2025-05-01 --end-date 2025-05-31
& .\.venv\Scripts\python.exe -m app.main extract-range --start-date 2025-06-01 --end-date 2025-06-30
```

### Load Raw JSON into PostgreSQL

Load everything:

```powershell
& .\.venv\Scripts\python.exe -m app.main load-raw --dataset all
```

Or load a single dataset:

```powershell
& .\.venv\Scripts\python.exe -m app.main load-raw --dataset sleep
```

## SQL Models

Raw tables:

- `raw_sleep`
- `raw_daily_health`
- `raw_activities`
- `raw_hrv`

Staging views:

- `stg_sleep`
- `stg_daily_health`
- `stg_activities`
- `stg_hrv`

Mart view:

- `mart_sleep_correlates_daily`

### Build or Refresh Staging Views

```powershell
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/staging/001_stg_sleep.sql
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/staging/002_stg_daily_health.sql
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/staging/003_stg_activities.sql
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/staging/004_stg_hrv.sql
```

### Build or Refresh the Mart

```powershell
& .\.venv\Scripts\python.exe -m app.main run-sql --file sql/marts/001_mart_sleep_correlates_daily.sql
```

The mart currently:

- keeps one row per sleep night
- joins same-day Garmin predictors
- includes lagged `prior_day_*` fields
- excludes incomplete nights where `sleep_score` or `sleep_duration_minutes` is null

## Dashboard

Start Streamlit:

```powershell
& .\.venv\Scripts\python.exe -m streamlit run dashboards/streamlit_app.py --server.port 8501
```

Then open:

- [http://localhost:8501](http://localhost:8501)

The dashboard includes:

- date filters
- key sleep and recovery KPIs
- sleep and recovery trend charts
- scatterplots for stress, steps, heart rate, and HRV
- a correlation summary against `sleep_score`
- recent-row and data-quality tables

## Validation Queries

Useful checks in `psql`:

```sql
select count(*) from raw_sleep;
select count(*) from raw_daily_health;
select count(*) from raw_activities;
select count(*) from raw_hrv;
```

```sql
select
    sleep_date,
    sleep_score,
    sleep_duration_minutes,
    avg_stress,
    steps,
    avg_heart_rate,
    resting_heart_rate,
    workout_count,
    hrv_value
from mart_sleep_correlates_daily
order by sleep_date desc
limit 20;
```

## Data Notes

- Garmin payloads can be null-heavy for incomplete or in-progress days.
- The mart excludes incomplete nights by default.
- Historical Garmin daily-health payloads may not include `heartRateValues`.
- In those cases, `stg_daily_health.avg_heart_rate` falls back to the midpoint of `minAvgHeartRate` and `maxAvgHeartRate`.
- Activity data is extracted as range-based JSON and then normalized to one row per day in `stg_activities`.

## Typical Workflow

For a new backfill or refresh:

1. Update `.env` with the latest Garmin MFA code if needed.
2. Run `login-test` if you want to verify authentication first.
3. Extract a recent or explicit date range.
4. Load raw JSON into PostgreSQL.
5. Refresh staging SQL files.
6. Refresh the mart SQL file.
7. Start Streamlit and review the dashboard.

## Next Improvements

Good follow-up tasks:

- add a notebook for exploratory analysis
- add weekday and rolling-average dashboard views
- document findings from the March-June 2025 sample
