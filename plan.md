# Garmin Sleep Factors Proof of Concept

## Overview

This project is a proof of concept that pulls data from Garmin Connect and explores how Garmin-tracked variables relate to nightly sleep outcomes.

The goal is not to make strong scientific claims or prove causation. The goal is to validate the project idea, build a clean data pipeline, and generate useful exploratory analysis from Garmin-only data.

## Objective

Build a Garmin-only analytics pipeline that:

1. extracts sleep, health, and activity data from Garmin Connect using Python,
2. stores raw API responses as JSON for traceability and reprocessing,
3. loads structured data into PostgreSQL,
4. transforms the data into analysis-ready tables using SQL,
5. displays findings in a Streamlit dashboard,
6. supports a short notebook-based analysis of which Garmin variables appear most associated with sleep.

## Core Question

How do Garmin-tracked variables such as stress, heart rate, resting heart rate, calories burned, steps, workouts, HRV, and sleep stages relate to nightly sleep quality and sleep duration?

## Project Scope

This is a proof of concept.

It will:
- use Garmin data only,
- focus on associations rather than causation,
- prioritize a small working end-to-end pipeline over feature completeness,
- tolerate missing or inconsistent optional metrics where needed.

It will not:
- include manual daily logging,
- attempt medical-grade conclusions,
- include orchestration in v1,
- overcomplicate the stack.

## Chosen Stack

- **Extraction:** Python
- **Garmin access:** unofficial Garmin Connect Python library
- **Raw storage:** JSON files
- **Warehouse:** PostgreSQL
- **Transformations:** plain SQL
- **Dashboard:** Streamlit
- **Analysis:** Jupyter notebook
- **Environment:** local Python + Docker Compose for PostgreSQL

## Data Sources

### Required metrics
These are the required Garmin metrics for v1:

- sleep score
- sleep duration
- stress
- average heart rate
- resting heart rate
- calories burned
- steps
- workouts or daily activity summary

### Included if reliably available
These should be included in v1 if extraction is reliable:

- HRV
- sleep stages such as deep sleep and REM sleep

### Explicitly excluded
These are out of scope for this version:

- manual logging
- respiration
- Body Battery

## Main Outcome Variables

### Primary target
- `sleep_score`

### Secondary target
- `sleep_duration_minutes`

### Additional sleep detail fields if available
- `deep_sleep_minutes`
- `rem_sleep_minutes`
- `light_sleep_minutes`
- `awake_minutes`
- `overnight_hrv`

## Analytical Design

The final analysis-ready table should have **one row per sleep night**.

Each row should represent a single night of sleep and include:
- that night's sleep outcomes,
- prior-day Garmin health and activity predictors,
- optional lagged fields where useful.

### Predictor alignment rule
Predictors should be aligned to the **preceding waking day**.

For example:
- sleep recorded for a given night should be paired with that same day's steps, calories, stress, workouts, and heart-related metrics.

This keeps the analytical structure intuitive and avoids mixing sleep with the wrong activity window.

## Storage Design

### Raw layer
Raw Garmin responses should be saved as JSON files under a raw data directory.

Suggested structure:

```text
/data/raw/
  sleep/
  daily_health/
  activities/
  hrv/
```

Why keep raw JSON:
- easier debugging,
- easier reprocessing,
- stronger project validation,
- avoids repeated API pulls during development.

### Structured warehouse layer
Structured tables should be loaded into PostgreSQL.

## Suggested Repository Structure

```text
garmin-sleep-poc/
├── app/
│   ├── extract/
│   │   ├── client.py
│   │   ├── extract_sleep.py
│   │   ├── extract_daily_health.py
│   │   ├── extract_activities.py
│   │   └── extract_hrv.py
│   ├── load/
│   │   ├── raw_writer.py
│   │   └── postgres_loader.py
│   ├── transform/
│   │   └── run_sql.py
│   ├── utils/
│   │   ├── config.py
│   │   └── logging.py
│   └── main.py
├── dashboards/
│   └── streamlit_app.py
├── data/
│   └── raw/
├── notebooks/
│   └── sleep_analysis.ipynb
├── sql/
│   ├── ddl/
│   ├── staging/
│   └── marts/
├── tests/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Warehouse Tables

### Raw ingestion tables
- `raw_sleep`
- `raw_daily_health`
- `raw_activities`
- `raw_hrv`

### Staging tables
- `stg_sleep`
- `stg_daily_health`
- `stg_activities`
- `stg_hrv`

### Mart tables
- `mart_sleep_correlates_daily`

## Key Mart Table Design

### `mart_sleep_correlates_daily`
One row per sleep night.

Suggested columns:

- `sleep_date`
- `sleep_score`
- `sleep_duration_minutes`
- `deep_sleep_minutes`
- `rem_sleep_minutes`
- `light_sleep_minutes`
- `awake_minutes`
- `avg_stress`
- `max_stress`
- `steps`
- `calories_burned`
- `avg_heart_rate`
- `resting_heart_rate`
- `workout_count`
- `activity_minutes`
- `hrv_value`
- `prior_day_steps`
- `prior_day_calories_burned`
- `prior_day_avg_stress`
- `prior_day_resting_heart_rate`

Only include columns that are reliably obtainable from Garmin data in practice.

## Transformation Strategy

Transformations will be written in plain SQL.

### SQL layers
- DDL scripts for table creation
- staging SQL to flatten and standardize raw records
- mart SQL to join nightly sleep outcomes with prior-day predictors

### Expected transformation tasks
- flatten Garmin JSON into relational columns,
- standardize timestamps and dates,
- derive daily activity summaries,
- derive workout count and activity duration,
- join sleep with prior-day predictors,
- handle missing optional fields safely.

## Dashboard Scope

The Streamlit dashboard should focus on a few useful views rather than trying to show everything.

### Suggested pages or sections

#### 1. Overview
- recent sleep score trend
- sleep duration trend
- key summary stats

#### 2. Sleep vs stress
- time series of sleep score and stress
- scatterplot of stress vs sleep score

#### 3. Sleep vs activity
- steps vs sleep
- calories vs sleep
- workouts vs sleep

#### 4. Sleep vs heart metrics
- resting heart rate vs sleep
- average heart rate vs sleep
- HRV vs sleep if available

#### 5. Correlation summary
- simple correlation heatmap
- strongest observed associations

## Notebook Analysis Scope

The notebook should complement the dashboard and answer the core question more directly.

### Suggested analyses
- descriptive statistics,
- missingness review,
- simple correlation matrix,
- scatterplots for top predictors,
- same-day vs lagged comparison,
- simple linear regression or feature ranking,
- short written summary of findings.

## Roadmap

### Version 1: Proof of Concept

This version focuses on proving the end-to-end concept works with Garmin data, PostgreSQL, SQL transformations, and a local dashboard.

#### Phase 1: Garmin access validation
Goal: confirm the account can be accessed and useful data can be pulled.

Tasks:
- set up Python environment,
- authenticate to Garmin,
- pull a small recent sample of sleep,
- pull daily health metrics,
- pull activities,
- test HRV and sleep stage availability,
- save raw JSON locally.

Exit criteria:
- successful login,
- successful pull of required metrics,
- raw JSON stored on disk.

#### Phase 2: Raw and warehouse ingestion
Goal: create repeatable raw storage and Postgres loading.

Tasks:
- create JSON directory structure,
- define raw and staging schemas,
- create Postgres tables,
- load raw files into raw tables,
- verify row counts and primary keys.

Exit criteria:
- required data lands in Postgres,
- raw and structured layers both exist.

#### Phase 3: SQL transformations
Goal: build an analysis-ready mart table.

Tasks:
- write staging SQL,
- normalize dates and timestamps,
- derive daily summaries,
- create `mart_sleep_correlates_daily`,
- validate joins and field completeness.

Exit criteria:
- one row per sleep night,
- primary predictors aligned correctly,
- mart table usable for charts and analysis.

#### Phase 4: Streamlit dashboard
Goal: create a working interactive dashboard.

Tasks:
- connect Streamlit to Postgres,
- build overview metrics,
- add trend charts,
- add scatterplots and correlations,
- add filters by date range if needed.

Exit criteria:
- dashboard runs locally,
- key relationships are visible.

#### Phase 5: Notebook and polish
Goal: make the POC presentable.

Tasks:
- create analysis notebook,
- summarize top observed relationships,
- clean README,
- document limitations,
- add screenshots if desired.

Exit criteria:
- repo is understandable,
- project story is easy to explain,
- outputs are demo-ready.

### Version 2

This version focuses on turning the proof of concept into a stronger data engineering portfolio project with better reliability, test coverage, observability, and presentation.

#### Part 1: Pipeline reliability and engineering discipline

Goal: make the pipeline safer to rerun, easier to validate, and more credible as a data engineering project.

Tasks:
- add a focused `pytest` suite for config loading, date range validation, raw JSON writing, and loader upsert behavior,
- add SQL-based data quality checks for null sleep outcomes, duplicate sleep dates, impossible durations, negative activity values, and outlier review,
- document idempotency clearly in the README, especially the `ON CONFLICT (source_file) DO UPDATE` raw load behavior,
- add a `pipeline_run_log` table to track run status, timestamps, load counts, and error messages,
- make validation checks part of the standard local pipeline workflow.

Exit criteria:
- core Python utilities have automated test coverage,
- mart quality checks can be run repeatedly and fail loudly when assumptions break,
- rerun safety and pipeline observability are documented and visible.

#### Part 2: Orchestration and portfolio polish

Goal: package the working pipeline as a more complete and demonstrable analytics system.

Tasks:
- add a lightweight orchestration layer such as Prefect to run extract, load, transform, validate, and logging steps in sequence,
- support scheduled or manually triggered pipeline runs,
- add an architecture diagram to the README, ideally as a Mermaid diagram,
- add screenshots of the dashboard, pipeline execution, and PostgreSQL objects to improve project presentation,
- extend the dashboard with a short `Key Findings` section that highlights strongest correlations, best and worst sleep nights, and recovery comparisons,
- evaluate a later migration to dbt for SQL model management, tests, docs, and lineage after orchestration and tests are in place.

Exit criteria:
- the pipeline can run through a single orchestrated workflow,
- the README clearly communicates architecture and outcomes,
- the dashboard answers a few concrete analytical questions rather than only showing charts,
- the repo presents well to recruiters and hiring managers.

## Risks and Fallback Rules

### Risk 1: unofficial Garmin access may be unstable
The Garmin extraction path depends on unofficial programmatic access.

Fallback:
- keep extraction logic isolated,
- store raw JSON once retrieved,
- avoid tightly coupling the whole project to repeated live pulls.

### Risk 2: optional endpoints may be inconsistent
HRV and sleep stages may not be consistently available.

Fallback:
- treat HRV and sleep stages as optional,
- do not block the rest of the pipeline if they fail,
- allow the mart and dashboard to degrade gracefully.

### Risk 3: limited historical completeness
Some metrics may not exist for all dates.

Fallback:
- allow nulls,
- filter analyses to available ranges,
- clearly document metric coverage.

## Success Criteria

The project is successful if it can:

- authenticate and pull Garmin data,
- store raw responses as JSON,
- load structured data into PostgreSQL,
- build a mart table centered on nightly sleep,
- show relationships between sleep and Garmin-tracked predictors in Streamlit,
- produce a short notebook summarizing observed associations.

## Non-Goals

This project does not aim to:
- establish causation,
- make medical or health recommendations,
- include advanced ML in v1,
- build enterprise-scale orchestration,
- perfectly model every Garmin metric.

## Final Summary

This project validates a focused data engineering and analytics use case:

**Garmin-only sleep analysis using Python, raw JSON, PostgreSQL, SQL transformations, and Streamlit.**

The final output should show whether Garmin-tracked variables such as stress, heart rate, calories, steps, workouts, HRV, and sleep-stage data appear to have observable relationships with nightly sleep outcomes, especially sleep score and sleep duration.
