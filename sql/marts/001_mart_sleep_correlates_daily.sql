CREATE OR REPLACE VIEW mart_sleep_correlates_daily AS
WITH joined AS (
    SELECT
        s.sleep_date,
        s.source_file AS sleep_source_file,
        s.sleep_score,
        s.sleep_duration_minutes,
        s.deep_sleep_minutes,
        s.rem_sleep_minutes,
        s.light_sleep_minutes,
        s.awake_minutes,
        s.avg_overnight_hrv,
        s.avg_sleep_stress,
        s.resting_heart_rate AS sleep_resting_heart_rate,
        s.sleep_feedback,
        s.sleep_score_insight,
        s.sleep_start_gmt,
        s.sleep_end_gmt,
        dh.source_file AS daily_health_source_file,
        dh.steps,
        dh.calories_burned,
        dh.avg_stress,
        dh.max_stress,
        dh.avg_heart_rate,
        dh.resting_heart_rate AS daily_resting_heart_rate,
        dh.total_distance_meters,
        dh.active_seconds,
        dh.highly_active_seconds,
        dh.stress_qualifier,
        a.source_file AS activities_source_file,
        COALESCE(a.workout_count, 0) AS workout_count,
        COALESCE(a.activity_minutes, 0) AS activity_minutes,
        COALESCE(a.activity_calories, 0) AS activity_calories,
        COALESCE(a.activity_distance_meters, 0) AS activity_distance_meters,
        h.source_file AS hrv_source_file,
        COALESCE(h.last_night_avg, s.avg_overnight_hrv) AS hrv_value,
        h.last_night_5min_high,
        h.weekly_avg AS hrv_weekly_avg,
        h.hrv_status
    FROM stg_sleep AS s
    LEFT JOIN stg_daily_health AS dh
        ON dh.calendar_date = s.sleep_date
    LEFT JOIN stg_activities AS a
        ON a.activity_date = s.sleep_date
    LEFT JOIN stg_hrv AS h
        ON h.calendar_date = s.sleep_date
    WHERE s.sleep_score IS NOT NULL
      AND s.sleep_duration_minutes IS NOT NULL
)
SELECT
    sleep_date,
    sleep_score,
    sleep_duration_minutes,
    deep_sleep_minutes,
    rem_sleep_minutes,
    light_sleep_minutes,
    awake_minutes,
    avg_stress,
    max_stress,
    steps,
    calories_burned,
    avg_heart_rate,
    COALESCE(sleep_resting_heart_rate, daily_resting_heart_rate) AS resting_heart_rate,
    workout_count,
    activity_minutes,
    hrv_value,
    LAG(steps) OVER (ORDER BY sleep_date) AS prior_day_steps,
    LAG(calories_burned) OVER (ORDER BY sleep_date) AS prior_day_calories_burned,
    LAG(avg_stress) OVER (ORDER BY sleep_date) AS prior_day_avg_stress,
    LAG(COALESCE(sleep_resting_heart_rate, daily_resting_heart_rate)) OVER (ORDER BY sleep_date) AS prior_day_resting_heart_rate,
    avg_overnight_hrv,
    avg_sleep_stress,
    total_distance_meters,
    active_seconds,
    highly_active_seconds,
    stress_qualifier,
    activity_calories,
    activity_distance_meters,
    last_night_5min_high,
    hrv_weekly_avg,
    hrv_status,
    sleep_feedback,
    sleep_score_insight,
    sleep_start_gmt,
    sleep_end_gmt,
    sleep_source_file,
    daily_health_source_file,
    activities_source_file,
    hrv_source_file
FROM joined
ORDER BY sleep_date;
