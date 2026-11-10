"""
Week 3 — Exploratory Data Analysis for Hypothetical Logistics Shipments

Run from the project root:
    python src/week3_eda_analysis.py

Reads:
    data/processed/week3_simulated_logistics.csv

Writes summary tables to:
    data/processed/

Writes presentation-ready charts to:
    outputs/charts/

All records are synthetic. Findings describe this simulation only.
"""

from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
CHART_DIR = ROOT / "outputs" / "charts"
INPUT_FILE = DATA_DIR / "week3_simulated_logistics.csv"

CHART_DIR.mkdir(parents=True, exist_ok=True)

# Continuous variables selected for statistical summaries and outlier review.
CONTINUOUS_COLUMNS = [
    "distance_km",
    "shipment_weight_kg",
    "shipment_volume_m3",
    "dispatch_delay_hours",
    "disruption_index",
    "handling_time_hours",
    "promised_delivery_days",
    "actual_delivery_days",
    "schedule_variance_days",
    "fuel_surcharge_inr",
    "transportation_cost_inr",
]

# These are variables available for descriptive association analysis.
# The derived schedule variance and late_delivery outcome are deliberately
# excluded because late_delivery is defined directly from schedule_variance_days.
CORRELATION_COLUMNS = [
    "distance_km",
    "shipment_weight_kg",
    "shipment_volume_m3",
    "dispatch_delay_hours",
    "disruption_index",
    "handling_time_hours",
    "promised_delivery_days",
    "actual_delivery_days",
    "fuel_surcharge_inr",
    "transportation_cost_inr",
]

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 250,
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
})




def spearman_correlation(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate Spearman correlation using ranked data and Pearson correlation.

    Ranking each column first is mathematically equivalent to Spearman's rho
    (with average ranks for ties) and avoids pandas' optional SciPy dependency.
    """
    ranked = frame.rank(method="average")
    return ranked.corr(method="pearson")


def save_chart(fig: plt.Figure, filename: str) -> None:
    """Save and close a chart so the script remains memory-efficient."""
    fig.tight_layout()
    destination = CHART_DIR / filename
    fig.savefig(destination, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Chart saved: {destination.relative_to(ROOT)}")


def validate_dataset(df: pd.DataFrame) -> dict[str, int | float | bool]:
    """Check required columns and key simulation logic before analysis."""
    required = {
        "shipment_id", "order_date", "region", "shipping_mode",
        *CONTINUOUS_COLUMNS, "late_delivery",
    }
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Required columns are missing: {missing_columns}")

    if df["shipment_id"].duplicated().any():
        raise ValueError("Shipment IDs are not unique.")

    if df.duplicated().any():
        raise ValueError("Exact duplicate rows were found.")

    if df.isna().any().any():
        raise ValueError("Missing values were found. Review the source dataset.")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="raise")

    if not set(df["late_delivery"].unique()).issubset({0, 1}):
        raise ValueError("late_delivery must contain only 0 and 1.")

    expected_late = (df["schedule_variance_days"] > 0).astype(int)
    target_matches = bool(expected_late.equals(df["late_delivery"].astype(int)))
    if not target_matches:
        raise ValueError(
            "late_delivery does not match the documented rule "
            "(schedule_variance_days > 0)."
        )

    calculated_variance = (
        df["actual_delivery_days"] - df["promised_delivery_days"]
    )
    max_variance_difference = float(
        (calculated_variance - df["schedule_variance_days"]).abs().max()
    )
    # The generator stores values rounded to two decimal places.
    if max_variance_difference > 0.011:
        raise ValueError(
            "Schedule variance does not reconcile with actual minus promised "
            f"delivery time. Maximum difference: {max_variance_difference:.4f}"
        )

    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_shipment_ids": int(df["shipment_id"].duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "late_rule_matches": target_matches,
        "max_variance_reconciliation_difference": max_variance_difference,
    }


def make_summary_tables(df: pd.DataFrame) -> None:
    """Create KPI, descriptive-statistics, group, monthly and outlier tables."""
    total = len(df)
    late_count = int(df["late_delivery"].sum())
    early_count = int((df["schedule_variance_days"] < 0).sum())
    on_schedule_count = int((df["schedule_variance_days"] == 0).sum())

    kpis = [
        ("Total shipments", total, "shipments"),
        ("Late shipments", late_count, "shipments"),
        ("Early shipments", early_count, "shipments"),
        ("Exactly on-schedule shipments", on_schedule_count, "shipments"),
        ("Late shipment rate", late_count / total * 100, "%"),
        ("Early shipment rate", early_count / total * 100, "%"),
        ("Exactly on-schedule rate", on_schedule_count / total * 100, "%"),
        ("Mean actual delivery time", df["actual_delivery_days"].mean(), "days"),
        ("Median actual delivery time", df["actual_delivery_days"].median(), "days"),
        ("Mean promised delivery time", df["promised_delivery_days"].mean(), "days"),
        ("Mean schedule variance", df["schedule_variance_days"].mean(), "days"),
        ("Mean transportation cost", df["transportation_cost_inr"].mean(), "INR"),
        ("Median transportation cost", df["transportation_cost_inr"].median(), "INR"),
        ("Mean shipment distance", df["distance_km"].mean(), "km"),
        ("Mean cost per kilometre", (df["transportation_cost_inr"] / df["distance_km"]).mean(), "INR/km"),
    ]
    pd.DataFrame(kpis, columns=["Metric", "Value", "Unit"]).to_csv(
        DATA_DIR / "week3_eda_kpi_summary.csv", index=False
    )

    rows = []
    for column in CONTINUOUS_COLUMNS:
        series = pd.to_numeric(df[column], errors="raise")
        modes = series.mode(dropna=True)
        rows.append({
            "Variable": column,
            "Count": int(series.count()),
            "Mean": series.mean(),
            "Median": series.median(),
            "Mode": modes.iloc[0] if not modes.empty else np.nan,
            "Standard Deviation": series.std(),
            "Minimum": series.min(),
            "Q1": series.quantile(0.25),
            "Q3": series.quantile(0.75),
            "Maximum": series.max(),
            "Skewness": series.skew(),
        })
    pd.DataFrame(rows).round(4).to_csv(
        DATA_DIR / "week3_eda_descriptive_statistics.csv", index=False
    )

    def grouped_summary(group_column: str) -> pd.DataFrame:
        grouped = df.groupby(group_column, dropna=False).agg(
            Shipments=("shipment_id", "count"),
            Late_Shipments=("late_delivery", "sum"),
            Late_Rate_pct=("late_delivery", "mean"),
            Mean_Actual_Delivery_Days=("actual_delivery_days", "mean"),
            Median_Actual_Delivery_Days=("actual_delivery_days", "median"),
            Mean_Promised_Delivery_Days=("promised_delivery_days", "mean"),
            Mean_Schedule_Variance_Days=("schedule_variance_days", "mean"),
            Mean_Transportation_Cost_INR=("transportation_cost_inr", "mean"),
            Median_Transportation_Cost_INR=("transportation_cost_inr", "median"),
            Mean_Distance_Km=("distance_km", "mean"),
        ).reset_index()

        grouped["Late_Rate_pct"] *= 100
        grouped["Mean_Cost_per_Km_INR"] = (
            grouped["Mean_Transportation_Cost_INR"] / grouped["Mean_Distance_Km"]
        )
        return grouped.round(3)

    grouped_summary("shipping_mode").to_csv(
        DATA_DIR / "week3_eda_by_shipping_mode.csv", index=False
    )
    grouped_summary("region").to_csv(
        DATA_DIR / "week3_eda_by_region.csv", index=False
    )

    monthly = df.assign(
        order_month=df["order_date"].dt.to_period("M").astype(str)
    ).groupby("order_month").agg(
        Shipments=("shipment_id", "count"),
        Late_Shipments=("late_delivery", "sum"),
        Late_Rate_pct=("late_delivery", "mean"),
        Mean_Actual_Delivery_Days=("actual_delivery_days", "mean"),
        Mean_Transportation_Cost_INR=("transportation_cost_inr", "mean"),
        Total_Transportation_Cost_INR=("transportation_cost_inr", "sum"),
    ).reset_index()
    monthly["Late_Rate_pct"] *= 100
    monthly.round(3).to_csv(
        DATA_DIR / "week3_eda_monthly_trends.csv", index=False
    )

    # IQR is used to flag observations for review, not to delete records.
    outlier_rows = []
    for column in CONTINUOUS_COLUMNS:
        series = df[column].dropna()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        flags = (series < lower) | (series > upper)
        outlier_rows.append({
            "Variable": column,
            "Q1": q1,
            "Q3": q3,
            "IQR": iqr,
            "Lower_Fence": lower,
            "Upper_Fence": upper,
            "Flagged_Records": int(flags.sum()),
            "Flagged_Percent": flags.mean() * 100,
            "Treatment": "Review; do not automatically remove",
        })
    pd.DataFrame(outlier_rows).round(4).to_csv(
        DATA_DIR / "week3_eda_iqr_outlier_review.csv", index=False
    )

    pearson = df[CORRELATION_COLUMNS].corr(method="pearson")
    spearman = spearman_correlation(df[CORRELATION_COLUMNS])
    pearson.to_csv(DATA_DIR / "week3_eda_pearson_correlations.csv")
    spearman.to_csv(DATA_DIR / "week3_eda_spearman_correlations.csv")

    pairs = []
    for i, first in enumerate(CORRELATION_COLUMNS):
        for second in CORRELATION_COLUMNS[i + 1:]:
            pairs.append({
                "Variable_1": first,
                "Variable_2": second,
                "Pearson_r": pearson.loc[first, second],
                "Spearman_rho": spearman.loc[first, second],
            })
    pairs_df = pd.DataFrame(pairs)
    pairs_df["Absolute_Spearman"] = pairs_df["Spearman_rho"].abs()
    pairs_df.sort_values("Absolute_Spearman", ascending=False).drop(
        columns="Absolute_Spearman"
    ).round(4).to_csv(
        DATA_DIR / "week3_eda_correlation_pairs.csv", index=False
    )


def make_charts(df: pd.DataFrame) -> None:
    """Generate charts that answer specific logistics performance questions."""

    # 1. Delivery outcome composition.
    outcome_counts = pd.Series({
        "Early": int((df["schedule_variance_days"] < 0).sum()),
        "Exactly on schedule": int((df["schedule_variance_days"] == 0).sum()),
        "Late": int(df["late_delivery"].sum()),
    })
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(outcome_counts.index, outcome_counts.values)
    ax.set_title("Week 3 — Shipment Delivery Outcomes")
    ax.set_ylabel("Number of shipments")
    ax.set_xlabel("Delivery outcome relative to promised date")
    for bar, value in zip(bars, outcome_counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{value:,}\n({value / len(df) * 100:.1f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(outcome_counts.values) * 1.18)
    save_chart(fig, "WEEK3_01_delivery_outcomes.png")

    # 2. Late-delivery rate by shipping mode, with group sizes.
    mode = df.groupby("shipping_mode").agg(
        Shipments=("shipment_id", "count"),
        Late_Rate=("late_delivery", "mean"),
    ).sort_values("Late_Rate", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(mode.index, mode["Late_Rate"] * 100)
    ax.set_title("Week 3 — Late-Delivery Rate by Shipping Mode")
    ax.set_ylabel("Late shipments (%)")
    ax.set_xlabel("Shipping mode")
    for bar, count, rate in zip(bars, mode["Shipments"], mode["Late_Rate"] * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{rate:.1f}%\n(n={count:,})",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(mode["Late_Rate"] * 100) * 1.2)
    save_chart(fig, "WEEK3_02_late_rate_by_shipping_mode.png")

    # 3. Late-delivery rate by region.
    region = df.groupby("region").agg(
        Shipments=("shipment_id", "count"),
        Late_Rate=("late_delivery", "mean"),
    ).sort_values("Late_Rate", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(region.index, region["Late_Rate"] * 100)
    ax.set_title("Week 3 — Late-Delivery Rate by Region")
    ax.set_ylabel("Late shipments (%)")
    ax.set_xlabel("Simulated region")
    for bar, count, rate in zip(bars, region["Shipments"], region["Late_Rate"] * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{rate:.1f}%\n(n={count:,})",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(region["Late_Rate"] * 100) * 1.2)
    save_chart(fig, "WEEK3_03_late_rate_by_region.png")

    # 4. Monthly shipment volume and late rate.
    monthly = df.assign(
        order_month=df["order_date"].dt.to_period("M").astype(str)
    ).groupby("order_month").agg(
        Shipments=("shipment_id", "count"),
        Late_Rate=("late_delivery", "mean"),
    ).reset_index()
    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(monthly))
    ax1.bar(x, monthly["Shipments"], alpha=0.75, label="Shipments")
    ax1.set_ylabel("Number of shipments")
    ax1.set_xlabel("Order month")
    ax1.set_xticks(x)
    ax1.set_xticklabels(monthly["order_month"], rotation=45, ha="right")
    ax1.set_title("Week 3 — Monthly Shipment Volume and Late-Delivery Rate")
    ax2 = ax1.twinx()
    ax2.plot(x, monthly["Late_Rate"] * 100, marker="o", linewidth=2,
             label="Late-delivery rate")
    ax2.set_ylabel("Late-delivery rate (%)")
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left")
    save_chart(fig, "WEEK3_04_monthly_volume_and_late_rate.png")

    # 5. Actual versus promised delivery time.
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["promised_delivery_days"], df["actual_delivery_days"],
               alpha=0.35, s=18)
    low = min(df["promised_delivery_days"].min(), df["actual_delivery_days"].min())
    high = max(df["promised_delivery_days"].max(), df["actual_delivery_days"].max())
    ax.plot([low, high], [low, high], linestyle="--", linewidth=1.5,
            label="Actual = promised")
    ax.set_title("Week 3 — Actual versus Promised Delivery Time")
    ax.set_xlabel("Promised delivery time (days)")
    ax.set_ylabel("Actual delivery time (days)")
    ax.legend()
    save_chart(fig, "WEEK3_05_actual_vs_promised_delivery.png")

    # 6. Distance versus transportation cost.
    rho = spearman_correlation(
        df[["distance_km", "transportation_cost_inr"]]
    ).loc["distance_km", "transportation_cost_inr"]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["distance_km"], df["transportation_cost_inr"],
               alpha=0.35, s=18)
    ax.set_title("Week 3 — Shipment Distance and Transportation Cost")
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Transportation cost (INR)")
    ax.text(0.03, 0.96, f"Spearman rank correlation = {rho:.3f}",
            transform=ax.transAxes, va="top",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85})
    save_chart(fig, "WEEK3_06_distance_vs_cost.png")

    # 7. Transportation cost distribution.
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(df["transportation_cost_inr"], bins=35, edgecolor="white")
    mean_cost = df["transportation_cost_inr"].mean()
    median_cost = df["transportation_cost_inr"].median()
    ax.axvline(mean_cost, linestyle="--", linewidth=2,
               label=f"Mean = INR {mean_cost:,.0f}")
    ax.axvline(median_cost, linestyle=":", linewidth=2,
               label=f"Median = INR {median_cost:,.0f}")
    ax.set_title("Week 3 — Distribution of Transportation Costs")
    ax.set_xlabel("Transportation cost (INR)")
    ax.set_ylabel("Number of shipments")
    ax.legend()
    save_chart(fig, "WEEK3_07_transportation_cost_distribution.png")

    # 8. Correlation heatmap for continuous operational and cost variables.
    corr = spearman_correlation(df[CORRELATION_COLUMNS])
    fig, ax = plt.subplots(figsize=(11, 9))
    image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=55, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    ax.set_title("Week 3 — Spearman Correlation between Operational Variables")
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}",
                    ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, label="Spearman correlation")
    save_chart(fig, "WEEK3_08_spearman_correlation_heatmap.png")

    # 9. Actual delivery-time distribution by shipping mode.
    order = ["Economy", "Standard", "Express"]
    available_order = [name for name in order if name in df["shipping_mode"].unique()]
    values = [
        df.loc[df["shipping_mode"] == name, "actual_delivery_days"].values
        for name in available_order
    ]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.boxplot(values, showfliers=False)
    ax.set_xticks(range(1, len(available_order) + 1))
    ax.set_xticklabels(available_order)
    ax.set_title("Week 3 — Actual Delivery-Time Distribution by Shipping Mode")
    ax.set_xlabel("Shipping mode")
    ax.set_ylabel("Actual delivery time (days)")
    save_chart(fig, "WEEK3_09_delivery_time_by_shipping_mode.png")


def main() -> None:
    print("=" * 72)
    print("WEEK 3 — EXPLORATORY DATA ANALYSIS")
    print("=" * 72)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}\n"
            "Run week3_generate_dataset.py first."
        )

    df = pd.read_csv(INPUT_FILE)
    validation = validate_dataset(df)

    print("\nDATA VALIDATION")
    for key, value in validation.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    print("\nDELIVERY OUTCOME CHECK")
    print(f"Early (variance < 0): {(df['schedule_variance_days'] < 0).sum():,}")
    print(f"Exactly on schedule: {(df['schedule_variance_days'] == 0).sum():,}")
    print(f"Late (variance > 0): {(df['schedule_variance_days'] > 0).sum():,}")
    print(
        "Note: early deliveries are not data errors. The late flag follows "
        "the documented positive-variance rule."
    )

    print("\nCREATING SUMMARY TABLES")
    make_summary_tables(df)

    print("\nCREATING VISUALIZATIONS")
    make_charts(df)

    print("\nEDA COMPLETE")
    print(f"Summary tables: {DATA_DIR}")
    print(f"Charts: {CHART_DIR}")
    print(
        "\nInterpretation reminder: all values are synthetic. Correlations "
        "describe the simulation and do not prove real-world causation."
    )


if __name__ == "__main__":
    main()
