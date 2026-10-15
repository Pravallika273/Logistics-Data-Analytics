"""
Week 2: Data Collection, Cleaning, and Preprocessing for Logistics Analysis

    python src/week2_data_preprocessing.py

Input:
    data/raw/DataCoSupplyChainDataset.csv

Outputs:
    data/processed/week2_*.csv
    outputs/charts/WEEK2_*.png

The script keeps a raw copy unchanged, documents cleaning decisions, flags rather
than automatically removes statistical outliers, and writes normalized numerical
features to a separate modelling-preparation file.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
CHART_DIR = ROOT / "outputs" / "charts"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)


def missing_profile(frame: pd.DataFrame) -> pd.DataFrame:
    """Return missing-value counts and percentages for every column."""
    missing_count = frame.isna().sum()
    profile = pd.DataFrame({
        "Column": frame.columns,
        "Missing Count": missing_count.values,
        "Missing Percent": (missing_count / max(len(frame), 1) * 100).values,
        "Non-Missing Count": (len(frame) - missing_count).values,
    })
    return profile.sort_values(
        ["Missing Count", "Column"], ascending=[False, True]
    ).reset_index(drop=True)


def safe_plot_path(name: str) -> Path:
    return CHART_DIR / name


if not RAW_FILE.exists():
    print(f"ERROR: Dataset not found:\n{RAW_FILE}")
    print("Place DataCoSupplyChainDataset.csv inside data/raw/ and run again.")
    sys.exit(1)

print("=" * 76)
print("WEEK 2 - LOGISTICS DATA COLLECTION, CLEANING AND PREPROCESSING")
print("=" * 76)

# ---------------------------------------------------------------------------
# 1. DATA COLLECTION / RAW DATA PROFILE
# ---------------------------------------------------------------------------
df_raw = pd.read_csv(RAW_FILE, encoding="latin-1", low_memory=False)
raw_rows, raw_columns = df_raw.shape

print(f"\nRaw dataset: {raw_rows:,} rows x {raw_columns:,} columns")
print(f"Exact duplicate rows before cleaning: {int(df_raw.duplicated().sum()):,}")

missing_before = missing_profile(df_raw)
missing_before.to_csv(
    PROCESSED_DIR / "week2_missing_values_before.csv", index=False
)

# Save a privacy-safe sample of relevant business fields only.
safe_sample_fields = [
    "Order Id", "Delivery Status", "Shipping Mode", "Market",
    "Days for shipping (real)", "Days for shipment (scheduled)",
    "Order Item Quantity", "Order Item Product Price", "Order Item Total",
]
safe_sample_fields = [c for c in safe_sample_fields if c in df_raw.columns]
df_raw[safe_sample_fields].head(12).to_csv(
    PROCESSED_DIR / "week2_before_cleaning_sample.csv", index=False
)

# ---------------------------------------------------------------------------
# 2. STANDARDIZE TYPES AND TEXT
# ---------------------------------------------------------------------------
df = df_raw.copy()

date_columns = [
    "order date (DateOrders)",
    "shipping date (DateOrders)",
]
for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

numeric_columns = [
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Benefit per order",
    "Sales per customer",
    "Latitude",
    "Longitude",
    "Order Item Discount",
    "Order Item Discount Rate",
    "Order Item Product Price",
    "Order Item Profit Ratio",
    "Order Item Quantity",
    "Sales",
    "Order Item Total",
    "Order Profit Per Order",
    "Product Price",
]
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

categorical_columns = [
    "Type", "Delivery Status", "Shipping Mode", "Market",
    "Customer Segment", "Order Status", "Order Region",
    "Order Country", "Customer Country", "Department Name",
    "Category Name", "Product Name",
]
for col in categorical_columns:
    if col in df.columns:
        # String dtype preserves missing values rather than converting them to "nan".
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace("", pd.NA)

# ---------------------------------------------------------------------------
# 3. CLEANING DECISIONS
# ---------------------------------------------------------------------------
decisions = []

# Remove exact duplicate rows only; don't assume repeated order IDs are duplicates,
# because an order can legitimately contain multiple line items.
duplicate_count = int(df.duplicated().sum())
if duplicate_count:
    df = df.drop_duplicates().copy()
decisions.append({
    "Issue": "Exact duplicate rows",
    "Observed": duplicate_count,
    "Action": "Removed exact duplicate rows" if duplicate_count else "No rows removed",
    "Rationale": "Only fully identical rows are treated as duplicates; repeated order IDs can represent valid line items.",
})

# High-missingness fields that are not needed for this delivery-performance task.
drop_reason = {
    "Product Description": "100% missing in the inspected dataset; it provides no usable information for this analysis.",
    "Order Zipcode": "Approximately 86% missing; it is not required for the selected shipping-mode and market analysis.",
    "Customer Email": "Direct personal identifier; not required for logistics KPI analysis.",
    "Customer Password": "Sensitive credential-like field; not required and should never be part of an analytical output.",
    "Customer Fname": "Direct personal identifier; not required for logistics KPI analysis.",
    "Customer Lname": "Direct personal identifier; not required for logistics KPI analysis.",
    "Customer Street": "Detailed personal location field; not required for the selected task.",
    "Customer Zipcode": "Fine-grained location identifier; not needed for the selected analysis, so no imputation is performed.",
}
columns_to_drop = [c for c in drop_reason if c in df.columns]
for col in columns_to_drop:
    missing_count = int(df[col].isna().sum())
    missing_pct = float(df[col].isna().mean() * 100)
    decisions.append({
        "Issue": f"Column removed: {col}",
        "Observed": f"{missing_count:,} missing ({missing_pct:.2f}%)",
        "Action": "Removed column",
        "Rationale": drop_reason[col],
    })
if columns_to_drop:
    df = df.drop(columns=columns_to_drop)

# Required fields for this Week 2 delivery-performance data layer.
required_columns = [
    "Order Id",
    "Delivery Status",
    "Shipping Mode",
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Order Item Total",
]
required_columns = [c for c in required_columns if c in df.columns]
if not required_columns:
    raise ValueError("Required logistics columns were not found. Check the source CSV.")

missing_required_mask = df[required_columns].isna().any(axis=1)
missing_required_rows = int(missing_required_mask.sum())
if missing_required_rows:
    df = df.loc[~missing_required_mask].copy()
decisions.append({
    "Issue": "Missing values in required analytical fields",
    "Observed": missing_required_rows,
    "Action": "Removed rows missing one or more required fields" if missing_required_rows else "No rows removed",
    "Rationale": "The selected KPI calculations need these fields. Optional fields are not blindly imputed.",
})

# Negative shipping-duration values are physically invalid for elapsed days.
actual_col = "Days for shipping (real)"
scheduled_col = "Days for shipment (scheduled)"
negative_duration_mask = pd.Series(False, index=df.index)
for col in [actual_col, scheduled_col]:
    if col in df.columns:
        negative_duration_mask |= df[col].lt(0).fillna(False)
negative_duration_rows = int(negative_duration_mask.sum())
if negative_duration_rows:
    df = df.loc[~negative_duration_mask].copy()
decisions.append({
    "Issue": "Negative actual/scheduled shipping days",
    "Observed": negative_duration_rows,
    "Action": "Removed rows with negative shipping duration" if negative_duration_rows else "No rows removed",
    "Rationale": "Elapsed shipping duration cannot be negative; rows are excluded only if this impossible condition exists.",
})

# Keep suspicious quantity/price/time-order cases as flags for investigation rather
# than automatically deleting them. For example, unusual quantities may represent
# returns, bundles or unusual orders.
flag_rows = []
if "Order Item Quantity" in df.columns:
    mask = df["Order Item Quantity"].le(0).fillna(False)
    flag_rows.append({
        "Quality Check": "Order Item Quantity <= 0",
        "Flagged Records": int(mask.sum()),
        "Percent of Cleaned Records": float(mask.mean() * 100),
        "Treatment": "Flagged for review; not automatically removed because the context may include returns or special transactions.",
    })
if "Order Item Product Price" in df.columns:
    mask = df["Order Item Product Price"].lt(0).fillna(False)
    flag_rows.append({
        "Quality Check": "Order Item Product Price < 0",
        "Flagged Records": int(mask.sum()),
        "Percent of Cleaned Records": float(mask.mean() * 100),
        "Treatment": "Flagged for review; investigate transaction meaning before exclusion.",
    })
if actual_col in df.columns and scheduled_col in df.columns:
    mask = df[actual_col].lt(0).fillna(False) | df[scheduled_col].lt(0).fillna(False)
    flag_rows.append({
        "Quality Check": "Negative shipping duration after cleaning",
        "Flagged Records": int(mask.sum()),
        "Percent of Cleaned Records": float(mask.mean() * 100),
        "Treatment": "Should be zero after the validity rule above.",
    })
order_date_col = "order date (DateOrders)"
ship_date_col = "shipping date (DateOrders)"
if order_date_col in df.columns and ship_date_col in df.columns:
    mask = (
        df[order_date_col].notna()
        & df[ship_date_col].notna()
        & (df[ship_date_col] < df[order_date_col])
    )
    flag_rows.append({
        "Quality Check": "Shipping date before order date",
        "Flagged Records": int(mask.sum()),
        "Percent of Cleaned Records": float(mask.mean() * 100),
        "Treatment": "Flag for investigation; do not silently change source dates.",
    })

quality_flags = pd.DataFrame(flag_rows)
if quality_flags.empty:
    quality_flags = pd.DataFrame(columns=[
        "Quality Check", "Flagged Records", "Percent of Cleaned Records", "Treatment"
    ])
quality_flags.to_csv(PROCESSED_DIR / "week2_data_quality_flags.csv", index=False)

# Derived feature: preserve actual and scheduled values so the variance remains traceable.
if actual_col in df.columns and scheduled_col in df.columns:
    df["Shipping Delay Days"] = df[actual_col] - df[scheduled_col]

# ---------------------------------------------------------------------------
# 4. OUTLIER REVIEW USING THE IQR RULE
# ---------------------------------------------------------------------------
outlier_columns = [
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Shipping Delay Days",
    "Order Item Quantity",
    "Order Item Product Price",
    "Order Item Total",
    "Sales",
    "Order Profit Per Order",
]
outlier_columns = [c for c in outlier_columns if c in df.columns]

outlier_records = []
for col in outlier_columns:
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    if values.empty:
        continue
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    flag = (values < low) | (values > high)
    outlier_records.append({
        "Column": col,
        "Non-Missing Records": int(values.size),
        "Q1": q1,
        "Q3": q3,
        "IQR": iqr,
        "Lower Fence": low,
        "Upper Fence": high,
        "Outlier Records": int(flag.sum()),
        "Outlier Percent": float(flag.mean() * 100),
        "Treatment": "Flagged, not automatically removed; business validation is needed because extreme orders/values may be legitimate.",
    })

outlier_summary = pd.DataFrame(outlier_records)
outlier_summary.to_csv(PROCESSED_DIR / "week2_outlier_summary.csv", index=False)

# ---------------------------------------------------------------------------
# 5. FEATURE NORMALIZATION (SEPARATE MODELLING PREPARATION OUTPUT)
# ---------------------------------------------------------------------------
normalization_columns = [
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Shipping Delay Days",
    "Order Item Quantity",
    "Order Item Product Price",
    "Order Item Total",
    "Sales",
    "Order Item Profit Ratio",
]
normalization_columns = [c for c in normalization_columns if c in df.columns]
numeric_for_scaling = df[normalization_columns].apply(pd.to_numeric, errors="coerce")

min_values = numeric_for_scaling.min()
max_values = numeric_for_scaling.max()
ranges = max_values - min_values
safe_ranges = ranges.mask(ranges.eq(0), 1)
normalized = (numeric_for_scaling - min_values) / safe_ranges
constant_features = ranges.index[ranges.eq(0)].tolist()
if constant_features:
    normalized.loc[:, constant_features] = 0
normalized.columns = [f"{col} (MinMax 0-1)" for col in normalized.columns]

# Keep identifiers out of this modelling-feature file.
normalized.to_csv(
    PROCESSED_DIR / "week2_normalized_features.csv", index=False
)

normalization_summary = []
for col in normalization_columns:
    raw_values = numeric_for_scaling[col]
    scaled_col = f"{col} (MinMax 0-1)"
    scaled_values = normalized[scaled_col]
    normalization_summary.append({
        "Feature": col,
        "Original Minimum": raw_values.min(),
        "Original Maximum": raw_values.max(),
        "Normalized Minimum": scaled_values.min(),
        "Normalized Maximum": scaled_values.max(),
        "Missing Values Preserved": int(scaled_values.isna().sum()),
        "Method": "Min-Max scaling: (x - min) / (max - min); constant columns map to 0.",
    })
pd.DataFrame(normalization_summary).to_csv(
    PROCESSED_DIR / "week2_normalization_summary.csv", index=False
)

# ---------------------------------------------------------------------------
# 6. AFTER-CLEANING PROFILES, DECISION LOG AND FINAL OUTPUTS
# ---------------------------------------------------------------------------
missing_after = missing_profile(df)
missing_after.to_csv(
    PROCESSED_DIR / "week2_missing_values_after.csv", index=False
)

df.to_csv(
    PROCESSED_DIR / "week2_cleaned_logistics.csv",
    index=False,
    date_format="%Y-%m-%d %H:%M:%S",
)

after_sample_fields = [
    "Order Id", "Delivery Status", "Shipping Mode", "Market",
    "Days for shipping (real)", "Days for shipment (scheduled)",
    "Shipping Delay Days", "Order Item Quantity",
    "Order Item Product Price", "Order Item Total",
]
after_sample_fields = [c for c in after_sample_fields if c in df.columns]
df[after_sample_fields].head(12).to_csv(
    PROCESSED_DIR / "week2_after_cleaning_sample.csv", index=False
)

pd.DataFrame(decisions).to_csv(
    PROCESSED_DIR / "week2_cleaning_decisions.csv", index=False
)

metrics = [
    ("Raw row count", raw_rows),
    ("Raw column count", raw_columns),
    ("Exact duplicate rows found", duplicate_count),
    ("Columns removed", len(columns_to_drop)),
    ("Rows removed for missing required fields", missing_required_rows),
    ("Rows removed for negative shipping durations", negative_duration_rows),
    ("Cleaned row count", len(df)),
    ("Cleaned column count", df.shape[1]),
    ("Remaining exact duplicate rows", int(df.duplicated().sum())),
    ("Missing cells before cleaning", int(df_raw.isna().sum().sum())),
    ("Missing cells after cleaning", int(df.isna().sum().sum())),
    ("Normalized numerical features", len(normalization_columns)),
]
summary = pd.DataFrame(metrics, columns=["Metric", "Value"])
summary.to_csv(PROCESSED_DIR / "week2_preprocessing_summary.csv", index=False)

# ---------------------------------------------------------------------------
# 7. VISUAL EVIDENCE
# ---------------------------------------------------------------------------
# Chart 1: before-cleaning missing value profile (only columns with missing values).
missing_nonzero = missing_before[missing_before["Missing Count"] > 0].head(12)
fig, ax = plt.subplots(figsize=(11, 6))
if not missing_nonzero.empty:
    chart_data = missing_nonzero.sort_values("Missing Percent", ascending=True)
    ax.barh(chart_data["Column"], chart_data["Missing Percent"])
    ax.set_xlabel("Missing Values (%)")
    ax.set_ylabel("Column")
    ax.set_title("Week 2: Missing-Value Profile Before Cleaning", weight="bold")
else:
    ax.text(0.5, 0.5, "No missing values detected", ha="center", va="center")
    ax.set_axis_off()
plt.tight_layout()
plt.savefig(safe_plot_path("WEEK2_01_missing_values_before.png"), dpi=250)
plt.close()

# Chart 2: IQR outlier prevalence.
fig, ax = plt.subplots(figsize=(11, 6))
if not outlier_summary.empty:
    chart_data = outlier_summary.sort_values("Outlier Percent", ascending=True)
    ax.barh(chart_data["Column"], chart_data["Outlier Percent"])
    ax.set_xlabel("Records outside IQR fences (%)")
    ax.set_ylabel("Numeric field")
    ax.set_title("Week 2: IQR-Based Outlier Flags (Review, Not Automatic Deletion)", weight="bold")
else:
    ax.text(0.5, 0.5, "No numeric fields available for IQR review", ha="center", va="center")
    ax.set_axis_off()
plt.tight_layout()
plt.savefig(safe_plot_path("WEEK2_02_outlier_review.png"), dpi=250)
plt.close()

# Chart 3: normalized feature distributions, all on the common 0-to-1 scale.
fig, ax = plt.subplots(figsize=(12, 6))
if normalized.shape[1] > 0:
    normalized.plot(kind="box", ax=ax, rot=25)
    ax.set_ylabel("Min-Max scaled value")
    ax.set_title("Week 2: Numerical Features After Min-Max Scaling", weight="bold")
    ax.set_ylim(-0.05, 1.05)
else:
    ax.text(0.5, 0.5, "No numeric features available for scaling", ha="center", va="center")
    ax.set_axis_off()
plt.tight_layout()
plt.savefig(safe_plot_path("WEEK2_03_normalized_features.png"), dpi=250)
plt.close()

print("\n" + "=" * 76)
print("WEEK 2 PREPROCESSING COMPLETE")
print("=" * 76)
print(summary.to_string(index=False))
print("\nHighest missing values BEFORE cleaning:")
print(missing_before[missing_before["Missing Count"] > 0].head(10).to_string(index=False))
print("\nIQR outlier review:")
if outlier_summary.empty:
    print("No numeric fields were available for outlier analysis.")
else:
    print(
        outlier_summary[["Column", "Outlier Records", "Outlier Percent"]]
        .round(2).to_string(index=False)
    )
print("\nFiles created in:")
print(PROCESSED_DIR)
print(CHART_DIR)
print("\nNote: Statistical outliers are flagged for review, not removed automatically.")
print("The full normalized file is a local modelling-preparation output; do not commit it to GitHub.")
