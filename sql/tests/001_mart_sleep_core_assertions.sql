DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM mart_sleep_correlates_daily
        WHERE sleep_score IS NULL
           OR sleep_duration_minutes IS NULL
    ) THEN
        RAISE EXCEPTION 'Quality check failed: mart_sleep_correlates_daily contains null core sleep fields.';
    END IF;

    IF EXISTS (
        SELECT sleep_date
        FROM mart_sleep_correlates_daily
        GROUP BY sleep_date
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Quality check failed: mart_sleep_correlates_daily contains duplicate sleep_date rows.';
    END IF;
END
$$;
