CREATE OR REPLACE VIEW stg_sleep AS
WITH sleep_base AS (
    SELECT
        raw_sleep_id,
        source_file,
        fetched_at,
        payload,
        COALESCE(
            NULLIF(payload -> 'dailySleepDTO' ->> 'calendarDate', '')::date,
            calendar_date
        ) AS sleep_date
    FROM raw_sleep
),
latest_sleep AS (
    SELECT DISTINCT ON (sleep_date)
        raw_sleep_id,
        sleep_date,
        source_file,
        fetched_at,
        payload
    FROM sleep_base
    WHERE sleep_date IS NOT NULL
    ORDER BY sleep_date, fetched_at DESC, raw_sleep_id DESC
)
SELECT
    raw_sleep_id,
    sleep_date,
    source_file,
    fetched_at,
    NULLIF(payload ->> 'avgOvernightHrv', '')::numeric AS avg_overnight_hrv,
    NULLIF(payload ->> 'bodyBatteryChange', '')::integer AS body_battery_change,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepTimeSeconds', '')::numeric / 60.0 AS sleep_duration_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'deepSleepSeconds', '')::numeric / 60.0 AS deep_sleep_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'lightSleepSeconds', '')::numeric / 60.0 AS light_sleep_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'remSleepSeconds', '')::numeric / 60.0 AS rem_sleep_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'awakeSleepSeconds', '')::numeric / 60.0 AS awake_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'avgSleepStress', '')::numeric AS avg_sleep_stress,
    NULLIF(payload ->> 'restingHeartRate', '')::integer AS resting_heart_rate,
    NULLIF(payload -> 'dailySleepDTO' -> 'sleepScores' -> 'overall' ->> 'value', '')::integer AS sleep_score,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepScoreFeedback', '') AS sleep_feedback,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepScoreInsight', '') AS sleep_score_insight,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepScorePersonalizedInsight', '') AS sleep_score_personalized_insight,
    NULLIF(payload -> 'dailySleepDTO' ->> 'awakeCount', '')::integer AS awake_count,
    NULLIF(payload -> 'dailySleepDTO' ->> 'napTimeSeconds', '')::numeric / 60.0 AS nap_minutes,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepVersion', '')::integer AS sleep_version,
    NULLIF(payload -> 'dailySleepDTO' ->> 'sleepWindowConfirmationType', '') AS sleep_window_confirmation_type,
    COALESCE(NULLIF(payload -> 'dailySleepDTO' ->> 'sleepWindowConfirmed', '')::boolean, FALSE) AS sleep_window_confirmed,
    TO_TIMESTAMP(NULLIF(payload -> 'dailySleepDTO' ->> 'sleepStartTimestampGMT', '')::double precision / 1000.0) AS sleep_start_gmt,
    TO_TIMESTAMP(NULLIF(payload -> 'dailySleepDTO' ->> 'sleepEndTimestampGMT', '')::double precision / 1000.0) AS sleep_end_gmt
FROM latest_sleep;
