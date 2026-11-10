from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "week3_simulated_logistics.csv"
OUTPUT_DIR = ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

numeric_columns = [
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

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# ---------------------------------------------------------
# 1. DATA VALIDATION
# ---------------------------------------------------------

variance_difference = (
    df["actual_delivery_days"]
    - df["promised_delivery_days"]
    - df["schedule_variance_days"]
).abs()

late_rule_mismatches = (
    df["late_delivery"]
    != (df["schedule_variance_days"] > 0).astype(int)
).sum()

validation = pd.DataFrame([
    ["Total records", len(df)],
    ["Total columns", len(df.columns)],
    ["Missing cells", int(df.isna().sum().sum())],
    ["Exact duplicate rows", int(df.duplicated().sum())],
    ["Duplicate shipment IDs", int(df["shipment_id"].duplicated().sum())],
    ["Invalid dates", int(df["order_date"].isna().sum())],
    ["Late-flag mismatches", int(late_rule_mismatches)],
    ["Maximum schedule variance reconciliation difference",
     float(variance_difference.max())],
    ["Negative distances", int(df["distance_km"].lt(0).sum())],
    ["Negative transportation costs",
     int(df["transportation_cost_inr"].lt(0).sum())],
], columns=["Validation Check", "Result"])

validation.to_csv(
    OUTPUT_DIR / "week3_deep_dive_validation.csv",
    index=False
)

# ---------------------------------------------------------
# 2. SERVICE MODE AND REGION COMPARISON
# ---------------------------------------------------------

def performance_summary(data, group_column):
    rows = []

    for name, part in data.groupby(group_column):
        total_distance = part["distance_km"].sum()
        total_cost = part["transportation_cost_inr"].sum()

        rows.append({
            group_column: name,
            "Shipments": len(part),
            "Late_Shipments": int(part["late_delivery"].sum()),
            "Late_Rate_pct": part["late_delivery"].mean() * 100,
            "Early_Rate_pct": (
                part["schedule_variance_days"].lt(0).mean() * 100
            ),
            "On_Schedule_Rate_pct": (
                part["schedule_variance_days"].eq(0).mean() * 100
            ),
            "Mean_Actual_Delivery_Days":
                part["actual_delivery_days"].mean(),
            "Median_Actual_Delivery_Days":
                part["actual_delivery_days"].median(),
            "Mean_Promised_Delivery_Days":
                part["promised_delivery_days"].mean(),
            "Mean_Schedule_Variance_Days":
                part["schedule_variance_days"].mean(),
            "Mean_Transportation_Cost_INR":
                part["transportation_cost_inr"].mean(),
            "Median_Transportation_Cost_INR":
                part["transportation_cost_inr"].median(),
            "Total_Transportation_Cost_INR": total_cost,
            "Weighted_Cost_per_Km_INR": (
                total_cost / total_distance if total_distance else np.nan
            ),
        })

    return pd.DataFrame(rows)


mode_summary = performance_summary(df, "shipping_mode")
region_summary = performance_summary(df, "region")

mode_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_by_service_mode.csv",
    index=False
)

region_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_by_region.csv",
    index=False
)

# ---------------------------------------------------------
# 3. MONTHLY AND QUARTERLY COMPARISON
# ---------------------------------------------------------

df["month"] = df["order_date"].dt.month
df["month_name"] = df["order_date"].dt.strftime("%b")
df["quarter"] = df["order_date"].dt.to_period("Q").astype(str)

monthly_summary = performance_summary(df, "month_name")
quarterly_summary = performance_summary(df, "quarter")

monthly_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_monthly.csv",
    index=False
)

quarterly_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_quarterly.csv",
    index=False
)

# Compare the final quarter against the rest of the year.
df["period_group"] = np.where(
    df["month"].ge(10),
    "Q4 (October-December)",
    "January-September"
)

peak_summary = performance_summary(df, "period_group")

peak_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_peak_period_comparison.csv",
    index=False
)

# ---------------------------------------------------------
# 4. DELIVERY OUTCOME AND COST COMPARISON
# ---------------------------------------------------------

df["delivery_outcome"] = np.select(
    [
        df["schedule_variance_days"] < 0,
        df["schedule_variance_days"] == 0,
        df["schedule_variance_days"] > 0,
    ],
    [
        "Early",
        "Exactly on Schedule",
        "Late",
    ],
    default="Review"
)

outcome_summary = (
    df.groupby("delivery_outcome")
    .agg(
        Shipments=("shipment_id", "count"),
        Mean_Actual_Delivery_Days=("actual_delivery_days", "mean"),
        Mean_Transportation_Cost_INR=("transportation_cost_inr", "mean"),
        Median_Transportation_Cost_INR=("transportation_cost_inr", "median"),
        Mean_Distance_Km=("distance_km", "mean"),
    )
    .reset_index()
)

outcome_summary.to_csv(
    OUTPUT_DIR / "week3_deep_dive_delivery_outcomes.csv",
    index=False
)

# ---------------------------------------------------------
# 5. COST AND DELIVERY PERCENTILES
# ---------------------------------------------------------

percentile_columns = [
    "distance_km",
    "actual_delivery_days",
    "schedule_variance_days",
    "transportation_cost_inr",
]

percentiles = df[percentile_columns].quantile(
    [0.50, 0.75, 0.90, 0.95, 0.99]
)

percentiles.index.name = "Percentile"
percentiles.to_csv(
    OUTPUT_DIR / "week3_deep_dive_percentiles.csv"
)

# Compare two definitions of cost per kilometre.
df["cost_per_km"] = (
    df["transportation_cost_inr"] / df["distance_km"]
)

cost_efficiency = pd.DataFrame([
    {
        "Metric": "Mean shipment-level cost per kilometre",
        "Value": df["cost_per_km"].mean(),
    },
    {
        "Metric": "Total cost divided by total distance",
        "Value": (
            df["transportation_cost_inr"].sum()
            / df["distance_km"].sum()
        ),
    },
])

cost_efficiency.to_csv(
    OUTPUT_DIR / "week3_deep_dive_cost_efficiency.csv",
    index=False
)

# ---------------------------------------------------------
# 6. CORRELATION AUDIT - NO SCIPY REQUIRED
# ---------------------------------------------------------

pairs = []

for first, second in combinations(numeric_columns, 2):
    first_series = df[first]
    second_series = df[second]

    pearson = first_series.corr(second_series)
    spearman = first_series.rank().corr(second_series.rank())

    pairs.append({
        "Variable_1": first,
        "Variable_2": second,
        "Pearson_r": pearson,
        "Spearman_rho": spearman,
    })

correlation_audit = pd.DataFrame(pairs)

correlation_audit["Absolute_Pearson"] = (
    correlation_audit["Pearson_r"].abs()
)

correlation_audit = correlation_audit.sort_values(
    "Absolute_Pearson",
    ascending=False
)

correlation_audit.drop(
    columns="Absolute_Pearson"
).to_csv(
    OUTPUT_DIR / "week3_deep_dive_correlation_pairs.csv",
    index=False
)

# ---------------------------------------------------------
# 7. GENERATE DATA-DRIVEN INTERPRETATION NOTES
# ---------------------------------------------------------

highest_mode = mode_summary.loc[
    mode_summary["Late_Rate_pct"].idxmax()
]

fastest_mode = mode_summary.loc[
    mode_summary["Mean_Actual_Delivery_Days"].idxmin()
]

highest_region = region_summary.loc[
    region_summary["Late_Rate_pct"].idxmax()
]

lowest_region = region_summary.loc[
    region_summary["Late_Rate_pct"].idxmin()
]

peak_row = peak_summary.loc[
    peak_summary["period_group"] == "Q4 (October-December)"
]

non_peak_row = peak_summary.loc[
    peak_summary["period_group"] == "January-September"
]

notes = [
    "WEEK 3 - DEEP-DIVE ANALYTICAL FINDINGS",
    "=" * 65,
    "",
    "DATA QUALITY",
    f"Records analysed: {len(df):,}",
    f"Missing cells: {int(df.isna().sum().sum()):,}",
    f"Duplicate shipment IDs: {int(df['shipment_id'].duplicated().sum()):,}",
    f"Late-flag mismatches: {int(late_rule_mismatches):,}",
    "",
    "SERVICE MODE",
    f"Highest late rate: {highest_mode['shipping_mode']} "
    f"({highest_mode['Late_Rate_pct']:.2f}%)",
    f"Fastest mean delivery: {fastest_mode['shipping_mode']} "
    f"({fastest_mode['Mean_Actual_Delivery_Days']:.2f} days)",
    "",
    "REGIONAL PERFORMANCE",
    f"Highest late rate: {highest_region['region']} "
    f"({highest_region['Late_Rate_pct']:.2f}%)",
    f"Lowest late rate: {lowest_region['region']} "
    f"({lowest_region['Late_Rate_pct']:.2f}%)",
    "",
    "SEASONAL COMPARISON",
]

if not peak_row.empty and not non_peak_row.empty:
    q4_rate = peak_row.iloc[0]["Late_Rate_pct"]
    other_rate = non_peak_row.iloc[0]["Late_Rate_pct"]

    notes.extend([
        f"Q4 late rate: {q4_rate:.2f}%",
        f"January-September late rate: {other_rate:.2f}%",
        f"Q4 difference: {q4_rate - other_rate:+.2f} percentage points",
    ])

notes.extend([
    "",
    "COST EFFICIENCY",
    f"Mean shipment-level cost per km: "
    f"INR {df['cost_per_km'].mean():.3f}",
    f"Weighted cost per km: "
    f"INR {df['transportation_cost_inr'].sum() / df['distance_km'].sum():.3f}",
    "",
    "INTERPRETATION LIMITATIONS",
    "- The dataset is synthetic.",
    "- Some relationships are built into its generation formulas.",
    "- Correlation does not establish causation.",
    "- Recommendations require validation using real operational data.",
])

notes_path = OUTPUT_DIR / "week3_deep_dive_findings.txt"
notes_path.write_text("\n".join(notes), encoding="utf-8")

# ---------------------------------------------------------
# 8. DISPLAY RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 75)
print("WEEK 3 - DEEP-DIVE ANALYSIS COMPLETED")
print("=" * 75)

print("\nDATA VALIDATION")
print(validation.to_string(index=False))

print("\nSERVICE-MODE COMPARISON")
print(mode_summary.round(3).to_string(index=False))

print("\nREGIONAL COMPARISON")
print(region_summary.round(3).to_string(index=False))

print("\nQUARTERLY COMPARISON")
print(quarterly_summary.round(3).to_string(index=False))

print("\nPEAK PERIOD COMPARISON")
print(peak_summary.round(3).to_string(index=False))

print("\nDELIVERY OUTCOME COMPARISON")
print(outcome_summary.round(3).to_string(index=False))

print("\nCOST EFFICIENCY")
print(cost_efficiency.round(3).to_string(index=False))

print("\nINTERPRETATION NOTES")
print("\n".join(notes))

print("\nAll additional analysis tables saved in:")
print(OUTPUT_DIR)