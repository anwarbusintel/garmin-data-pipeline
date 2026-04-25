from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from app.utils.config import get_settings

settings = get_settings()

NUMERIC_COLUMNS = [
    "sleep_score",
    "sleep_duration_minutes",
    "deep_sleep_minutes",
    "rem_sleep_minutes",
    "light_sleep_minutes",
    "awake_minutes",
    "avg_stress",
    "max_stress",
    "steps",
    "calories_burned",
    "avg_heart_rate",
    "resting_heart_rate",
    "workout_count",
    "activity_minutes",
    "hrv_value",
    "prior_day_steps",
    "prior_day_calories_burned",
    "prior_day_avg_stress",
    "prior_day_resting_heart_rate",
    "avg_overnight_hrv",
    "avg_sleep_stress",
    "total_distance_meters",
    "active_seconds",
    "highly_active_seconds",
    "activity_calories",
    "activity_distance_meters",
    "last_night_5min_high",
    "hrv_weekly_avg",
]

st.set_page_config(page_title="Garmin Sleep Dashboard", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def load_mart_data(sqlalchemy_url: str) -> pd.DataFrame:
    engine = create_engine(sqlalchemy_url)
    query = text("SELECT * FROM mart_sleep_correlates_daily ORDER BY sleep_date")
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)

    if df.empty:
        return df

    df["sleep_date"] = pd.to_datetime(df["sleep_date"])
    for column in ("sleep_start_gmt", "sleep_end_gmt"):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def format_minutes_as_hours(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    hours = value / 60.0
    return f"{hours:.1f} hrs"


def format_decimal(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.{digits}f}"


def format_signed_decimal(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:+.{digits}f}"


def build_sleep_score_correlation_summary(df: pd.DataFrame) -> pd.DataFrame:
    correlation_columns = [
        "avg_stress",
        "steps",
        "calories_burned",
        "avg_heart_rate",
        "resting_heart_rate",
        "workout_count",
        "activity_minutes",
        "hrv_value",
        "prior_day_steps",
        "prior_day_calories_burned",
        "prior_day_avg_stress",
        "prior_day_resting_heart_rate",
    ]
    available_columns = [
        column for column in correlation_columns if column in df.columns and df[column].notna().any()
    ]
    if not available_columns:
        return pd.DataFrame(columns=["metric", "correlation_with_sleep_score"])

    correlation_df = (
        df[["sleep_score", *available_columns]]
        .corr(numeric_only=True)["sleep_score"]
        .drop(labels=["sleep_score"])
        .dropna()
        .sort_values(key=lambda series: series.abs(), ascending=False)
        .rename_axis("metric")
        .reset_index(name="correlation_with_sleep_score")
    )
    return correlation_df


st.title("Garmin Sleep Dashboard")
st.caption("Interactive review of nightly sleep outcomes and same-day Garmin predictors.")

try:
    mart_df = load_mart_data(settings.sqlalchemy_url)
except Exception as exc:
    st.error(f"Failed to load `mart_sleep_correlates_daily`: {exc}")
    st.stop()

if mart_df.empty:
    st.warning("`mart_sleep_correlates_daily` is empty. Load raw data and refresh the mart view first.")
    st.stop()

min_date = mart_df["sleep_date"].min().date()
max_date = mart_df["sleep_date"].max().date()
default_start = max(min_date, max_date - timedelta(days=60))

st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Sleep Date Range",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

show_only_hrv = st.sidebar.checkbox("Only nights with HRV", value=False)

filtered_df = mart_df[
    (mart_df["sleep_date"].dt.date >= start_date)
    & (mart_df["sleep_date"].dt.date <= end_date)
].copy()

if show_only_hrv:
    filtered_df = filtered_df[filtered_df["hrv_value"].notna()].copy()

if filtered_df.empty:
    st.info("No rows match the current filters.")
    st.stop()

overview_tab, relationships_tab, data_tab = st.tabs(["Overview", "Relationships", "Data"])

with overview_tab:
    metric_cols = st.columns(5)
    metric_cols[0].metric("Nights", f"{len(filtered_df)}")
    metric_cols[1].metric("Avg Sleep Score", format_decimal(filtered_df["sleep_score"].mean()))
    metric_cols[2].metric(
        "Avg Sleep Duration",
        format_minutes_as_hours(filtered_df["sleep_duration_minutes"].mean()),
    )
    metric_cols[3].metric("Avg Stress", format_decimal(filtered_df["avg_stress"].mean()))
    metric_cols[4].metric("Avg HRV", format_decimal(filtered_df["hrv_value"].mean()))

    st.subheader("Coverage")
    st.write(
        f"Showing `{len(filtered_df)}` nights from `{start_date}` to `{end_date}`."
    )
    coverage_cols = st.columns(4)
    coverage_cols[0].metric("Nights With HRV", f"{filtered_df['hrv_value'].notna().sum()}")
    coverage_cols[1].metric("Nights With Avg HR", f"{filtered_df['avg_heart_rate'].notna().sum()}")
    coverage_cols[2].metric("Workout Nights", f"{(filtered_df['workout_count'] > 0).sum()}")
    coverage_cols[3].metric("Avg Steps", format_decimal(filtered_df["steps"].mean(), 0))

    st.subheader("Key Findings")
    sleep_score_corr = build_sleep_score_correlation_summary(filtered_df)
    strongest_positive = sleep_score_corr[
        sleep_score_corr["correlation_with_sleep_score"] > 0
    ].head(1)
    strongest_negative = sleep_score_corr[
        sleep_score_corr["correlation_with_sleep_score"] < 0
    ].head(1)

    workout_days_df = filtered_df[filtered_df["workout_count"].fillna(0) > 0]
    non_workout_days_df = filtered_df[filtered_df["workout_count"].fillna(0) <= 0]
    workout_score_delta = (
        workout_days_df["sleep_score"].mean() - non_workout_days_df["sleep_score"].mean()
        if not workout_days_df.empty and not non_workout_days_df.empty
        else None
    )

    findings_cols = st.columns(3)
    with findings_cols[0]:
        if not strongest_positive.empty:
            row = strongest_positive.iloc[0]
            st.metric(
                "Top Positive Correlation",
                row["metric"],
                format_signed_decimal(row["correlation_with_sleep_score"]),
            )
        else:
            st.metric("Top Positive Correlation", "-", "-")

    with findings_cols[1]:
        if not strongest_negative.empty:
            row = strongest_negative.iloc[0]
            st.metric(
                "Top Negative Correlation",
                row["metric"],
                format_signed_decimal(row["correlation_with_sleep_score"]),
            )
        else:
            st.metric("Top Negative Correlation", "-", "-")

    with findings_cols[2]:
        if workout_score_delta is not None:
            st.metric(
                "Workout vs No Workout",
                format_decimal(workout_days_df["sleep_score"].mean()),
                format_signed_decimal(workout_score_delta),
            )
        else:
            st.metric("Workout vs No Workout", "-", "-")

    best_nights = (
        filtered_df.sort_values(["sleep_score", "sleep_duration_minutes"], ascending=[False, False])
        .head(5)[["sleep_date", "sleep_score", "sleep_duration_minutes", "avg_stress", "hrv_value"]]
        .copy()
    )
    worst_nights = (
        filtered_df.sort_values(["sleep_score", "sleep_duration_minutes"], ascending=[True, True])
        .head(5)[["sleep_date", "sleep_score", "sleep_duration_minutes", "avg_stress", "hrv_value"]]
        .copy()
    )
    for finding_df in (best_nights, worst_nights):
        finding_df["sleep_date"] = finding_df["sleep_date"].dt.date

    summary_lines: list[str] = []
    if not strongest_positive.empty:
        row = strongest_positive.iloc[0]
        summary_lines.append(
            f"- Strongest positive relationship with `sleep_score`: `{row['metric']}` ({format_signed_decimal(row['correlation_with_sleep_score'])})."
        )
    if not strongest_negative.empty:
        row = strongest_negative.iloc[0]
        summary_lines.append(
            f"- Strongest negative relationship with `sleep_score`: `{row['metric']}` ({format_signed_decimal(row['correlation_with_sleep_score'])})."
        )
    if workout_score_delta is not None:
        summary_lines.append(
            f"- Average `sleep_score` on workout days: `{format_decimal(workout_days_df['sleep_score'].mean())}` "
            f"vs `{format_decimal(non_workout_days_df['sleep_score'].mean())}` on non-workout days."
        )
    if not worst_nights.empty:
        worst_row = worst_nights.iloc[0]
        summary_lines.append(
            f"- Lowest-scoring visible night: `{worst_row['sleep_date']}` with `sleep_score` `{format_decimal(worst_row['sleep_score'])}` "
            f"and `avg_stress` `{format_decimal(worst_row['avg_stress'])}`."
        )
    if summary_lines:
        st.markdown("\n".join(summary_lines))

    findings_left, findings_right = st.columns(2)
    with findings_left:
        st.caption("Best 5 nights in the current filter window")
        st.dataframe(best_nights, use_container_width=True, hide_index=True)
    with findings_right:
        st.caption("Worst 5 nights in the current filter window")
        st.dataframe(worst_nights, use_container_width=True, hide_index=True)

    trend_left, trend_right = st.columns(2)
    with trend_left:
        st.subheader("Sleep Trend")
        sleep_trend = filtered_df.set_index("sleep_date")[
            ["sleep_score", "sleep_duration_minutes"]
        ]
        st.line_chart(sleep_trend, use_container_width=True)

    with trend_right:
        st.subheader("Recovery Trend")
        recovery_trend = filtered_df.set_index("sleep_date")[
            ["avg_stress", "hrv_value", "resting_heart_rate"]
        ]
        st.line_chart(recovery_trend, use_container_width=True)

    stage_cols = st.columns(4)
    stage_cols[0].metric("Avg Deep Sleep", format_minutes_as_hours(filtered_df["deep_sleep_minutes"].mean()))
    stage_cols[1].metric("Avg REM Sleep", format_minutes_as_hours(filtered_df["rem_sleep_minutes"].mean()))
    stage_cols[2].metric("Avg Light Sleep", format_minutes_as_hours(filtered_df["light_sleep_minutes"].mean()))
    stage_cols[3].metric("Avg Awake Time", format_minutes_as_hours(filtered_df["awake_minutes"].mean()))

    st.caption(
        "`avg_heart_rate` uses Garmin sample-level values when available and falls back to the midpoint of "
        "`minAvgHeartRate` and `maxAvgHeartRate` for historical periods where Garmin omits the time series."
    )

with relationships_tab:
    scatter_left, scatter_right = st.columns(2)
    with scatter_left:
        st.subheader("Sleep Score vs Stress")
        stress_scatter = filtered_df[["avg_stress", "sleep_score"]].dropna()
        st.scatter_chart(
            stress_scatter,
            x="avg_stress",
            y="sleep_score",
            use_container_width=True,
        )

        st.subheader("Sleep Score vs Steps")
        steps_scatter = filtered_df[["steps", "sleep_score"]].dropna()
        st.scatter_chart(
            steps_scatter,
            x="steps",
            y="sleep_score",
            use_container_width=True,
        )

    with scatter_right:
        st.subheader("Sleep Score vs Resting Heart Rate")
        hr_scatter = filtered_df[["resting_heart_rate", "sleep_score"]].dropna()
        st.scatter_chart(
            hr_scatter,
            x="resting_heart_rate",
            y="sleep_score",
            use_container_width=True,
        )

        st.subheader("Sleep Score vs HRV")
        hrv_scatter = filtered_df[["hrv_value", "sleep_score"]].dropna()
        st.scatter_chart(
            hrv_scatter,
            x="hrv_value",
            y="sleep_score",
            use_container_width=True,
        )

    st.subheader("Correlation Snapshot")
    sleep_score_corr = build_sleep_score_correlation_summary(filtered_df)
    st.dataframe(sleep_score_corr, use_container_width=True, hide_index=True)

with data_tab:
    st.subheader("Recent Rows")
    display_columns = [
        "sleep_date",
        "sleep_score",
        "sleep_duration_minutes",
        "avg_stress",
        "steps",
        "calories_burned",
        "avg_heart_rate",
        "resting_heart_rate",
        "workout_count",
        "activity_minutes",
        "hrv_value",
    ]
    available_display_columns = [col for col in display_columns if col in filtered_df.columns]
    st.dataframe(
        filtered_df.sort_values("sleep_date", ascending=False)[available_display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Data Quality")
    quality_columns = [
        "sleep_score",
        "sleep_duration_minutes",
        "avg_stress",
        "steps",
        "avg_heart_rate",
        "resting_heart_rate",
        "hrv_value",
    ]
    quality_df = pd.DataFrame(
        {
            "column": quality_columns,
            "non_null_rows": [int(filtered_df[column].notna().sum()) for column in quality_columns],
            "null_rows": [int(filtered_df[column].isna().sum()) for column in quality_columns],
        }
    )
    st.dataframe(quality_df, use_container_width=True, hide_index=True)
