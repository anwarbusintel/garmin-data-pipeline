DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM mart_sleep_correlates_daily
        WHERE sleep_duration_minutes < 0
           OR sleep_duration_minutes > 1440
    ) THEN
        RAISE EXCEPTION 'Quality check failed: sleep_duration_minutes falls outside 0-1440.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM mart_sleep_correlates_daily
        WHERE COALESCE(steps, 0) < 0
           OR COALESCE(calories_burned, 0) < 0
           OR COALESCE(activity_minutes, 0) < 0
    ) THEN
        RAISE EXCEPTION 'Quality check failed: mart contains negative activity values.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM mart_sleep_correlates_daily
        WHERE hrv_value IS NOT NULL
          AND (hrv_value < 0 OR hrv_value > 250)
    ) THEN
        RAISE EXCEPTION 'Quality check failed: hrv_value falls outside expected 0-250 bounds.';
    END IF;
END
$$;
