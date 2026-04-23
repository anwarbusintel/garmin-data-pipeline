CREATE OR REPLACE VIEW stg_hrv AS
WITH hrv_base AS (
    SELECT
        raw_hrv_id,
        source_file,
        fetched_at,
        payload,
        COALESCE(
            NULLIF(payload -> 'hrvSummary' ->> 'calendarDate', '')::date,
            calendar_date
        ) AS calendar_date
    FROM raw_hrv
),
latest_hrv AS (
    SELECT DISTINCT ON (calendar_date)
        raw_hrv_id,
        calendar_date,
        source_file,
        fetched_at,
        payload
    FROM hrv_base
    WHERE calendar_date IS NOT NULL
    ORDER BY calendar_date, fetched_at DESC, raw_hrv_id DESC
)
SELECT
    lh.raw_hrv_id,
    lh.calendar_date,
    lh.source_file,
    lh.fetched_at,
    NULLIF(lh.payload -> 'hrvSummary' ->> 'lastNightAvg', '')::numeric AS last_night_avg,
    NULLIF(lh.payload -> 'hrvSummary' ->> 'lastNight5MinHigh', '')::numeric AS last_night_5min_high,
    NULLIF(lh.payload -> 'hrvSummary' ->> 'weeklyAvg', '')::numeric AS weekly_avg,
    NULLIF(lh.payload -> 'hrvSummary' ->> 'status', '') AS hrv_status,
    NULLIF(lh.payload -> 'hrvSummary' -> 'baseline' ->> 'balancedLow', '')::numeric AS baseline_balanced_low,
    NULLIF(lh.payload -> 'hrvSummary' -> 'baseline' ->> 'balancedUpper', '')::numeric AS baseline_balanced_upper,
    NULLIF(lh.payload -> 'hrvSummary' -> 'baseline' ->> 'unbalancedLow', '')::numeric AS baseline_unbalanced_low,
    NULLIF(lh.payload -> 'hrvSummary' -> 'baseline' ->> 'markerValue', '')::numeric AS baseline_marker_value,
    (NULLIF(lh.payload ->> 'sleepStartTimestampGMT', '')::timestamp AT TIME ZONE 'UTC') AS sleep_start_gmt,
    (NULLIF(lh.payload ->> 'sleepEndTimestampGMT', '')::timestamp AT TIME ZONE 'UTC') AS sleep_end_gmt,
    readings.reading_count,
    readings.avg_hrv_reading,
    readings.max_hrv_reading
FROM latest_hrv AS lh
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS reading_count,
        AVG(NULLIF(reading ->> 'hrvValue', '')::numeric) AS avg_hrv_reading,
        MAX(NULLIF(reading ->> 'hrvValue', '')::numeric) AS max_hrv_reading
    FROM JSONB_ARRAY_ELEMENTS(COALESCE(lh.payload -> 'hrvReadings', '[]'::jsonb)) AS reading
    WHERE NULLIF(reading ->> 'hrvValue', '') IS NOT NULL
) AS readings ON TRUE;
