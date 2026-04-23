CREATE OR REPLACE VIEW stg_daily_health AS
WITH daily_health_base AS (
    SELECT
        raw_daily_health_id,
        source_file,
        fetched_at,
        payload,
        COALESCE(
            NULLIF(payload ->> 'calendar_date', '')::date,
            NULLIF(payload -> 'stats' ->> 'calendarDate', '')::date,
            calendar_date
        ) AS calendar_date
    FROM raw_daily_health
),
latest_daily_health AS (
    SELECT DISTINCT ON (calendar_date)
        raw_daily_health_id,
        calendar_date,
        source_file,
        fetched_at,
        payload
    FROM daily_health_base
    WHERE calendar_date IS NOT NULL
    ORDER BY calendar_date, fetched_at DESC, raw_daily_health_id DESC
)
SELECT
    ldh.raw_daily_health_id,
    ldh.calendar_date,
    ldh.source_file,
    ldh.fetched_at,
    NULLIF(ldh.payload -> 'stats' ->> 'totalSteps', '')::integer AS steps,
    NULLIF(ldh.payload -> 'stats' ->> 'totalKilocalories', '')::numeric AS calories_burned,
    NULLIF(ldh.payload -> 'stats' ->> 'wellnessKilocalories', '')::numeric AS wellness_calories,
    NULLIF(ldh.payload -> 'stats' ->> 'activeKilocalories', '')::numeric AS active_calories,
    NULLIF(ldh.payload -> 'stats' ->> 'averageStressLevel', '')::numeric AS avg_stress,
    NULLIF(ldh.payload -> 'stats' ->> 'maxStressLevel', '')::integer AS max_stress,
    NULLIF(ldh.payload -> 'stats' ->> 'restingHeartRate', '')::integer AS resting_heart_rate,
    NULLIF(ldh.payload -> 'heart_rates' ->> 'maxHeartRate', '')::integer AS max_heart_rate,
    NULLIF(ldh.payload -> 'heart_rates' ->> 'minHeartRate', '')::integer AS min_heart_rate,
    COALESCE(
        hr.avg_heart_rate,
        (
            NULLIF(ldh.payload -> 'stats' ->> 'maxAvgHeartRate', '')::numeric
            + NULLIF(ldh.payload -> 'stats' ->> 'minAvgHeartRate', '')::numeric
        ) / 2.0,
        NULLIF(ldh.payload -> 'stats' ->> 'maxAvgHeartRate', '')::numeric,
        NULLIF(ldh.payload -> 'stats' ->> 'minAvgHeartRate', '')::numeric
    ) AS avg_heart_rate,
    NULLIF(ldh.payload -> 'stats' ->> 'totalDistanceMeters', '')::numeric AS total_distance_meters,
    NULLIF(ldh.payload -> 'stats' ->> 'activeSeconds', '')::integer AS active_seconds,
    NULLIF(ldh.payload -> 'stats' ->> 'highlyActiveSeconds', '')::integer AS highly_active_seconds,
    NULLIF(ldh.payload -> 'stats' ->> 'sleepingSeconds', '')::integer AS sleeping_seconds,
    NULLIF(ldh.payload -> 'stats' ->> 'stressQualifier', '') AS stress_qualifier,
    NULLIF(ldh.payload -> 'stress' ->> 'avgStressLevel', '')::numeric AS stress_avg_from_stress_payload,
    NULLIF(ldh.payload -> 'stress' ->> 'maxStressLevel', '')::integer AS stress_max_from_stress_payload,
    NULLIF(ldh.payload -> 'stats' ->> 'maxAvgHeartRate', '')::numeric AS max_avg_heart_rate,
    NULLIF(ldh.payload -> 'stats' ->> 'minAvgHeartRate', '')::numeric AS min_avg_heart_rate
FROM latest_daily_health AS ldh
LEFT JOIN LATERAL (
    SELECT AVG(NULLIF(entry ->> 1, '')::numeric) AS avg_heart_rate
    FROM JSONB_ARRAY_ELEMENTS(
        CASE
            WHEN JSONB_TYPEOF(ldh.payload -> 'heart_rates' -> 'heartRateValues') = 'array'
                THEN ldh.payload -> 'heart_rates' -> 'heartRateValues'
            ELSE '[]'::jsonb
        END
    ) AS entry
    WHERE JSONB_TYPEOF(entry) = 'array'
      AND NULLIF(entry ->> 1, '') IS NOT NULL
) AS hr ON TRUE;
