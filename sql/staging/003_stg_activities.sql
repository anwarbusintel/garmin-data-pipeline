CREATE OR REPLACE VIEW stg_activities AS
WITH activity_ranges AS (
    SELECT
        raw_activity_id,
        source_file,
        fetched_at,
        payload,
        NULLIF(payload ->> 'start_date', '')::date AS start_date,
        NULLIF(payload ->> 'end_date', '')::date AS end_date,
        NULLIF(payload ->> 'activity_count', '')::integer AS activity_count_in_range
    FROM raw_activities
    WHERE NULLIF(payload ->> 'start_date', '') IS NOT NULL
      AND NULLIF(payload ->> 'end_date', '') IS NOT NULL
),
activity_dates AS (
    SELECT
        ar.raw_activity_id,
        ar.source_file,
        ar.fetched_at,
        ar.payload,
        ar.start_date,
        ar.end_date,
        ar.activity_count_in_range,
        gs::date AS activity_date
    FROM activity_ranges AS ar
    CROSS JOIN LATERAL GENERATE_SERIES(ar.start_date, ar.end_date, INTERVAL '1 day') AS gs
),
latest_activity_ranges AS (
    SELECT DISTINCT ON (activity_date)
        raw_activity_id,
        activity_date,
        source_file,
        fetched_at,
        payload,
        start_date,
        end_date,
        activity_count_in_range
    FROM activity_dates
    ORDER BY activity_date, fetched_at DESC, raw_activity_id DESC
),
activity_payloads AS (
    SELECT DISTINCT
        raw_activity_id,
        source_file,
        payload
    FROM latest_activity_ranges
),
parsed_activities AS (
    SELECT
        ap.raw_activity_id,
        ap.source_file,
        (
            COALESCE(
                SUBSTRING(NULLIF(activity ->> 'activityDate', '') FROM 1 FOR 10),
                SUBSTRING(NULLIF(activity ->> 'startTimeLocal', '') FROM 1 FOR 10),
                SUBSTRING(NULLIF(activity ->> 'startTimeGMT', '') FROM 1 FOR 10),
                SUBSTRING(NULLIF(activity -> 'summaryDTO' ->> 'startTimeLocal', '') FROM 1 FOR 10),
                SUBSTRING(NULLIF(activity -> 'summaryDTO' ->> 'startTimeGMT', '') FROM 1 FOR 10)
            )
        )::date AS activity_record_date,
        NULLIF(
            COALESCE(
                activity ->> 'duration',
                activity ->> 'durationInSeconds',
                activity ->> 'elapsedDuration',
                activity -> 'summaryDTO' ->> 'duration'
            ),
            ''
        )::numeric AS duration_seconds,
        NULLIF(
            COALESCE(
                activity ->> 'calories',
                activity -> 'summaryDTO' ->> 'calories'
            ),
            ''
        )::numeric AS calories,
        NULLIF(
            COALESCE(
                activity ->> 'distance',
                activity -> 'summaryDTO' ->> 'distance'
            ),
            ''
        )::numeric AS distance_meters
    FROM activity_payloads AS ap
    LEFT JOIN LATERAL JSONB_ARRAY_ELEMENTS(COALESCE(ap.payload -> 'activities', '[]'::jsonb)) AS activity ON TRUE
)
SELECT
    lar.activity_date,
    lar.source_file,
    lar.fetched_at,
    lar.start_date AS range_start_date,
    lar.end_date AS range_end_date,
    lar.activity_count_in_range,
    COUNT(pa.activity_record_date) AS workout_count,
    ROUND(COALESCE(SUM(pa.duration_seconds), 0) / 60.0, 2) AS activity_minutes,
    COALESCE(SUM(pa.calories), 0) AS activity_calories,
    COALESCE(SUM(pa.distance_meters), 0) AS activity_distance_meters
FROM latest_activity_ranges AS lar
LEFT JOIN parsed_activities AS pa
    ON pa.raw_activity_id = lar.raw_activity_id
   AND pa.activity_record_date = lar.activity_date
GROUP BY
    lar.activity_date,
    lar.source_file,
    lar.fetched_at,
    lar.start_date,
    lar.end_date,
    lar.activity_count_in_range;
