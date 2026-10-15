"""
Create polished Week 2 report charts from the verified Week 2 CSV outputs.

Run from the project root:
    python src/week2_create_report_visuals.py

Does not modify the raw or cleaned datasets.
"""
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

required = [
    DATA / "week2_missing_values_before.csv",
    DATA / "week2_outlier_summary.csv",
    DATA / "week2_normalized_features.csv",
    DATA / "week2_cleaned_logistics.csv",
]
missing_files = [str(p) for p in required if not p.exists()]
if missing_files:
    print("Missing required outputs. Run week2_data_preprocessing.py first:")
    print("\n".join(missing_files))
    sys.exit(1)

missing = pd.read_csv(DATA / "week2_missing_values_before.csv")
outliers = pd.read_csv(DATA / "week2_outlier_summary.csv")
normalized = pd.read_csv(DATA / "week2_normalized_features.csv")

# Chart 1: split major and minor missingness into separate panels so both are legible.
missing = missing.loc[missing["Missing Count"] > 0].copy()
missing["Missing Percent"] = pd.to_numeric(missing["Missing Percent"], errors="coerce")
missing["Missing Count"] = pd.to_numeric(missing["Missing Count"], errors="coerce")
high = missing.loc[missing["Missing Percent"] >= 1].sort_values("Missing Percent")
low = missing.loc[missing["Missing Percent"] < 1].sort_values("Missing Percent")

fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [2.1, 1.4]})
if not high.empty:
    bars = axes[0].barh(high["Column"], high["Missing Percent"])
    axes[0].set_xlim(0, 105)
    axes[0].set_xlabel("Missing values (%)")
    axes[0].set_title("High missingness", weight="bold")
    for bar, (_, row) in zip(bars, high.iterrows()):
        axes[0].text(
            bar.get_width() - 1.5,
            bar.get_y() + bar.get_height() / 2,
            f'{row["Missing Percent"]:.2f}% (n={int(row["Missing Count"]):,})',
            va="center",
            ha="right",
            fontsize=9,
            color="white",
            fontweight="bold"
        )
if not low.empty:
    bars = axes[1].barh(low["Column"], low["Missing Percent"])
    axes[1].set_xlim(0, max(float(low["Missing Percent"].max()) * 2, 0.01))
    axes[1].set_xlabel("Missing values (%)")
    axes[1].set_title("Very low missingness", weight="bold")
    for bar, (_, row) in zip(bars, low.iterrows()):
        axes[1].text(bar.get_width() + max(float(low["Missing Percent"].max()) * .04, .0001),
                     bar.get_y() + bar.get_height()/2,
                     f'{row["Missing Percent"]:.4f}% (n={int(row["Missing Count"]):,})',
                     va="center", fontsize=9)
fig.suptitle("Week 2 — Missing-Value Profile Before Cleaning", fontsize=17, weight="bold")
fig.text(.5, .01, "Separate scales keep both large and very small percentages readable.",
         ha="center", fontsize=9)
plt.tight_layout(rect=[0, .04, 1, .92])
plt.savefig(CHARTS / "WEEK2_REPORT_01_missingness.png", dpi=250, bbox_inches="tight")
plt.close(fig)

# Chart 2: IQR flags with counts, clearly labelled as investigation candidates.
outliers["Outlier Percent"] = pd.to_numeric(outliers["Outlier Percent"], errors="coerce")
outliers["Outlier Records"] = pd.to_numeric(outliers["Outlier Records"], errors="coerce")
outliers = outliers.sort_values("Outlier Percent", ascending=True)
fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(outliers["Column"], outliers["Outlier Percent"])
max_pct = float(outliers["Outlier Percent"].max())
ax.set_xlim(0, max(max_pct * 1.4, 2))
ax.set_xlabel("Records outside IQR fences (%)")
ax.set_title("Week 2 — IQR Outlier Flags by Numerical Field", fontsize=17, weight="bold")
for bar, (_, row) in zip(bars, outliers.iterrows()):
    ax.text(bar.get_width() + max(max_pct * .025, .15),
            bar.get_y() + bar.get_height()/2,
            f'{row["Outlier Percent"]:.2f}% (n={int(row["Outlier Records"]):,})',
            va="center", fontsize=9)
fig.text(.5, .01, "Flags indicate values for investigation; they are not automatic deletion decisions.",
         ha="center", fontsize=9)
plt.tight_layout(rect=[0, .04, 1, 1])
plt.savefig(CHARTS / "WEEK2_REPORT_02_iqr_outliers.png", dpi=250, bbox_inches="tight")
plt.close(fig)

# Chart 3: frequency of actual-minus-scheduled days. Read only the required column.
delay = pd.read_csv(DATA / "week2_cleaned_logistics.csv",
                    usecols=["Shipping Delay Days"])["Shipping Delay Days"]
delay = pd.to_numeric(delay, errors="coerce").dropna()
counts = delay.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(11, 6))
bars = ax.bar([str(int(x)) for x in counts.index], counts.values)
ax.set_xlabel("Actual shipping days − scheduled shipping days")
ax.set_ylabel("Number of records")
ax.set_title("Week 2 — Distribution of Shipping Schedule Variance", fontsize=17, weight="bold")
for bar, count in zip(bars, counts.values):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(counts.values)*.012,
            f"{int(count):,}", ha="center", va="bottom", fontsize=9)
fig.text(
    0.5,
    0.015,
    "IQR fences: -1.5 to +2.5 days. Integer values -2, +3 and +4 are flagged.",
    ha="center",
    va="bottom",
    fontsize=9
)
plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig(CHARTS / "WEEK2_REPORT_03_delay_distribution.png", dpi=250, bbox_inches="tight")
plt.close(fig)

# Chart 4: shorten labels and hide fliers only in this plot for legibility.
short_labels = {
    "Days for shipping (real) (MinMax 0-1)": "Actual ship days",
    "Days for shipment (scheduled) (MinMax 0-1)": "Scheduled ship days",
    "Shipping Delay Days (MinMax 0-1)": "Schedule variance",
    "Order Item Quantity (MinMax 0-1)": "Item quantity",
    "Order Item Product Price (MinMax 0-1)": "Product price",
    "Order Item Total (MinMax 0-1)": "Item total",
    "Sales (MinMax 0-1)": "Sales",
    "Order Item Profit Ratio (MinMax 0-1)": "Profit ratio",
}
normalized = normalized.rename(columns=short_labels)
fig, ax = plt.subplots(figsize=(13, 6))
normalized.plot(kind="box", ax=ax, showfliers=False, grid=True, rot=25)
ax.set_ylabel("Min-Max scaled value")
ax.set_ylim(-.05, 1.05)
ax.set_title("Week 2 — Normalized Numerical Features (0–1 Scale)", fontsize=17, weight="bold")
fig.text(.5, .01, "Outlier markers are hidden for readability only; no records were deleted.",
         ha="center", fontsize=9)
plt.tight_layout(rect=[0, .04, 1, 1])
plt.savefig(CHARTS / "WEEK2_REPORT_04_normalized_features.png", dpi=250, bbox_inches="tight")
plt.close(fig)

print("=" * 70)
print("WEEK 2 REPORT VISUALS CREATED")
print("=" * 70)
for name in [
    "WEEK2_REPORT_01_missingness.png",
    "WEEK2_REPORT_02_iqr_outliers.png",
    "WEEK2_REPORT_03_delay_distribution.png",
    "WEEK2_REPORT_04_normalized_features.png",
]:
    path = CHARTS / name
    print(f"{path} | {path.stat().st_size:,} bytes")
print("\nRaw and validated cleaned data were not modified.")
