"""Generate a reproducible hypothetical logistics shipment dataset for YuvaIntern Week 3.

Run from the project root:
    python src/week3_generate_dataset.py

The generated records are synthetic and do not describe a real company or actual shipments.
A fixed random seed makes the dataset reproducible. The script writes only to
    data/processed/
and does not modify the Week 1 or Week 2 files.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RANDOM_SEED = 20261104
N_SHIPMENTS = 5_000
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DATA_PATH = OUTPUT_DIR / "week3_simulated_logistics.csv"
PROFILE_PATH = OUTPUT_DIR / "week3_dataset_profile.csv"
DICTIONARY_PATH = OUTPUT_DIR / "week3_dataset_dictionary.csv"
ASSUMPTIONS_PATH = OUTPUT_DIR / "week3_simulation_assumptions.txt"


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------
def generate_dataset(n: int = N_SHIPMENTS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Create n synthetic shipment records using documented assumptions."""
    if n <= 0:
        raise ValueError("n must be a positive integer")

    rng = np.random.default_rng(seed)

    regions = np.array(["North", "South", "East", "West", "Central"])
    region_probabilities = np.array([0.22, 0.22, 0.19, 0.22, 0.15])
    region = rng.choice(regions, size=n, p=region_probabilities)

    shipping_modes = np.array(["Economy", "Standard", "Express"])
    mode_probabilities = np.array([0.25, 0.50, 0.25])
    shipping_mode = rng.choice(shipping_modes, size=n, p=mode_probabilities)

    # Uniform order dates across the simulated calendar year.
    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)
    days_in_period = (end - start).days + 1
    order_date = start + pd.to_timedelta(
        rng.integers(0, days_in_period, size=n), unit="D"
    )

    # Right-skewed operational quantities, bounded to avoid implausible extremes.
    distance_km = np.clip(rng.lognormal(mean=6.45, sigma=0.62, size=n), 40, 2_000)
    shipment_weight_kg = np.clip(
        rng.lognormal(mean=3.55, sigma=0.78, size=n), 5, 600
    )
    volume_noise = rng.gamma(shape=1.8, scale=0.055, size=n)
    shipment_volume_m3 = np.clip(
        shipment_weight_kg / 250 + volume_noise, 0.02, 3.5
    )

    # Operational delay and disruption indicators.
    dispatch_delay_hours = np.clip(
        rng.gamma(shape=2.0, scale=2.0, size=n), 0, 20
    )
    disruption_index = rng.beta(a=2.0, b=5.0, size=n)

    region_handling_add = {
        "North": 0.05,
        "South": 0.12,
        "East": 0.18,
        "West": 0.08,
        "Central": 0.15,
    }
    region_disruption_add = {
        "North": 0.00,
        "South": 0.04,
        "East": 0.10,
        "West": 0.02,
        "Central": 0.07,
    }
    region_cost_factor = {
        "North": 1.00,
        "South": 1.03,
        "East": 1.05,
        "West": 1.02,
        "Central": 1.04,
    }

    # Slight simulated peak-period pressure in October–December.
    peak_period = np.isin(order_date.month, [10, 11, 12]).astype(float)
    region_handling = pd.Series(region).map(region_handling_add).to_numpy()
    region_disruption = pd.Series(region).map(region_disruption_add).to_numpy()
    region_cost = pd.Series(region).map(region_cost_factor).to_numpy()

    handling_time_hours = (
        1.5
        + 0.012 * shipment_weight_kg
        + 0.8 * shipment_volume_m3
        + region_handling
        + 0.35 * peak_period
        + rng.normal(loc=0.0, scale=0.55, size=n)
    )
    handling_time_hours = np.clip(handling_time_hours, 0.5, 18)

    # Mode-specific nominal transit speed and promised-service buffer.
    speed_km_per_day = pd.Series(shipping_mode).map(
        {"Economy": 520.0, "Standard": 720.0, "Express": 1_000.0}
    ).to_numpy()
    sla_buffer_days = pd.Series(shipping_mode).map(
        {"Economy": 0.88, "Standard": 0.78, "Express": 0.68}
    ).to_numpy()

    base_transit_days = distance_km / speed_km_per_day
    promised_delivery_days = base_transit_days + sla_buffer_days

    # Actual duration includes dispatch, handling, disruption, regional/seasonal
    # pressure, and random operational variation.
    operational_delay_days = (
        dispatch_delay_hours / 24
        + handling_time_hours / 24
        + 0.95 * disruption_index
        + region_disruption
        + 0.12 * peak_period
        + rng.normal(loc=0.0, scale=0.20, size=n)
    )
    actual_delivery_days = np.clip(
        base_transit_days + operational_delay_days, 0.2, None
    )

    # Round durations for realistic reporting precision, then derive the target
    # from the rounded source values so the relationship is fully consistent.
    promised_delivery_days = np.round(promised_delivery_days, 2)
    actual_delivery_days = np.round(actual_delivery_days, 2)
    schedule_variance_days = np.round(
        actual_delivery_days - promised_delivery_days, 2
    )
    late_delivery = (schedule_variance_days > 0).astype("int8")

    # Simulated INR cost model. Fuel surcharge is an explicit component of total
    # transport cost; the remaining line-haul/handling cost is modelled separately.
    mode_cost_multiplier = pd.Series(shipping_mode).map(
        {"Economy": 0.90, "Standard": 1.00, "Express": 1.27}
    ).to_numpy()
    fuel_index = np.clip(rng.normal(loc=1.0, scale=0.07, size=n), 0.82, 1.20)

    fuel_surcharge_inr = (
        0.13 * distance_km + 0.55 * shipment_weight_kg
    ) * fuel_index
    linehaul_and_handling_inr = (
        95
        + 0.62 * distance_km
        + 3.8 * shipment_weight_kg
        + 42 * shipment_volume_m3
        + 6.0 * handling_time_hours
    ) * mode_cost_multiplier * region_cost
    cost_noise = rng.normal(loc=1.0, scale=0.045, size=n)
    transportation_cost_inr = (
        linehaul_and_handling_inr + fuel_surcharge_inr
    ) * np.clip(cost_noise, 0.85, 1.15)

    shipment_ids = [f"SHP{i:06d}" for i in range(1, n + 1)]

    df = pd.DataFrame(
        {
            "shipment_id": shipment_ids,
            "order_date": order_date.strftime("%Y-%m-%d"),
            "region": region,
            "shipping_mode": shipping_mode,
            "distance_km": np.round(distance_km, 2),
            "shipment_weight_kg": np.round(shipment_weight_kg, 2),
            "shipment_volume_m3": np.round(shipment_volume_m3, 3),
            "dispatch_delay_hours": np.round(dispatch_delay_hours, 2),
            "disruption_index": np.round(disruption_index, 4),
            "handling_time_hours": np.round(handling_time_hours, 2),
            "promised_delivery_days": promised_delivery_days,
            "actual_delivery_days": actual_delivery_days,
            "schedule_variance_days": schedule_variance_days,
            "late_delivery": late_delivery,
            "fuel_surcharge_inr": np.round(fuel_surcharge_inr, 2),
            "transportation_cost_inr": np.round(transportation_cost_inr, 2),
        }
    )
    return df


# ---------------------------------------------------------------------------
# Profile, data dictionary and validation
# ---------------------------------------------------------------------------
def create_profile(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for column in df.columns:
        series = df[column]
        record = {
            "column": column,
            "data_type": str(series.dtype),
            "non_missing_count": int(series.notna().sum()),
            "missing_count": int(series.isna().sum()),
            "unique_values": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            record.update(
                {
                    "minimum": round(float(series.min()), 4),
                    "mean": round(float(series.mean()), 4),
                    "median": round(float(series.median()), 4),
                    "maximum": round(float(series.max()), 4),
                }
            )
        else:
            record.update(
                {"minimum": "", "mean": "", "median": "", "maximum": ""}
            )
        records.append(record)
    return pd.DataFrame(records)


def create_dictionary() -> pd.DataFrame:
    definitions = [
        ("shipment_id", "Unique synthetic shipment identifier", "Identifier"),
        ("order_date", "Synthetic order date between 2025-01-01 and 2025-12-31", "Date"),
        ("region", "Synthetic operating region: North, South, East, West or Central", "Categorical"),
        ("shipping_mode", "Synthetic service mode: Economy, Standard or Express", "Categorical"),
        ("distance_km", "Simulated shipment distance in kilometres", "Numerical; km"),
        ("shipment_weight_kg", "Simulated shipment weight in kilograms", "Numerical; kg"),
        ("shipment_volume_m3", "Simulated shipment volume in cubic metres", "Numerical; m3"),
        ("dispatch_delay_hours", "Simulated elapsed dispatch delay in hours", "Numerical; hours"),
        ("disruption_index", "Synthetic disruption intensity between 0 and 1", "Index; unitless"),
        ("handling_time_hours", "Simulated warehouse/handling time in hours", "Numerical; hours"),
        ("promised_delivery_days", "Simulated promised delivery duration in days", "Numerical; days"),
        ("actual_delivery_days", "Simulated actual delivery duration in days", "Numerical; days"),
        ("schedule_variance_days", "Actual delivery days minus promised delivery days", "Derived; days"),
        ("late_delivery", "1 when schedule variance is positive; otherwise 0", "Binary target"),
        ("fuel_surcharge_inr", "Simulated fuel surcharge component in INR", "Numerical; INR"),
        ("transportation_cost_inr", "Simulated total transportation cost in INR, including fuel surcharge", "Numerical; INR"),
    ]
    return pd.DataFrame(definitions, columns=["column", "definition", "type_or_unit"])


def validate_dataset(df: pd.DataFrame) -> None:
    expected_columns = 16
    if len(df) != N_SHIPMENTS:
        raise AssertionError(f"Expected {N_SHIPMENTS} rows, found {len(df)}")
    if df.shape[1] != expected_columns:
        raise AssertionError(f"Expected {expected_columns} columns, found {df.shape[1]}")
    if df["shipment_id"].duplicated().any():
        raise AssertionError("Shipment IDs are not unique")
    if df.isna().any().any():
        raise AssertionError("Generated dataset contains missing values")
    non_negative_columns = [
        "distance_km", "shipment_weight_kg", "shipment_volume_m3",
        "dispatch_delay_hours", "handling_time_hours",
        "promised_delivery_days", "actual_delivery_days",
        "fuel_surcharge_inr", "transportation_cost_inr",
    ]
    for column in non_negative_columns:
        if (df[column] < 0).any():
            raise AssertionError(f"Negative values found in {column}")
    if not df["disruption_index"].between(0, 1).all():
        raise AssertionError("disruption_index must remain between 0 and 1")
    expected_variance = (
        df["actual_delivery_days"] - df["promised_delivery_days"]
    ).round(2)
    if not np.allclose(expected_variance, df["schedule_variance_days"]):
        raise AssertionError("Schedule variance does not match actual minus promised days")
    expected_late = (df["schedule_variance_days"] > 0).astype("int8")
    if not (expected_late == df["late_delivery"]).all():
        raise AssertionError("late_delivery flag does not match schedule variance")
    if (df["transportation_cost_inr"] < df["fuel_surcharge_inr"]).any():
        raise AssertionError("Total transportation cost cannot be below fuel surcharge")


def write_assumptions(df: pd.DataFrame) -> None:
    mode_counts = df["shipping_mode"].value_counts().sort_index()
    region_counts = df["region"].value_counts().sort_index()
    late_rate = df["late_delivery"].mean() * 100

    lines = [
        "WEEK 3 — HYPOTHETICAL LOGISTICS DATASET: SIMULATION NOTES",
        "=" * 68,
        "",
        "IMPORTANT: All records and values are synthetic. They do not represent",
        "a real logistics company, customer, carrier, shipment or market observation.",
        "The dataset is designed only to demonstrate exploratory analysis and",
        "visualization techniques for the Week 3 assignment.",
        "",
        f"Rows: {len(df):,}",
        f"Columns: {df.shape[1]}",
        f"Random seed: {RANDOM_SEED}",
        f"Simulated order-date period: {START_DATE} to {END_DATE}",
        "",
        "GENERATION ASSUMPTIONS",
        "1. Shipment IDs are unique identifiers generated sequentially.",
        "2. Regions and shipping modes are assigned using fixed probabilities.",
        "3. Distance, weight and volume are generated from bounded, right-skewed distributions.",
        "4. Dispatch delay, handling time and disruption are simulated operational factors.",
        "5. Nominal transit time is distance divided by a mode-specific assumed speed.",
        "6. Promised delivery time is nominal transit time plus a mode-specific SLA buffer.",
        "7. Actual delivery time includes dispatch delay, handling time, disruption,",
        "   regional/peak-period adjustments and random variation.",
        "8. Schedule variance = actual delivery days - promised delivery days.",
        "9. Late delivery = 1 when schedule variance is greater than zero; else 0.",
        "10. Transportation cost is simulated from distance, weight, volume, handling,",
        "    shipping-mode multiplier, regional factor and a fuel-surcharge component.",
        "11. October–December include a small assumed peak-period pressure adjustment.",
        "",
        "SIMULATED CATEGORY COUNTS",
        "Shipping mode:",
    ]
    lines.extend([f"  - {name}: {count:,}" for name, count in mode_counts.items()])
    lines.append("Regions:")
    lines.extend([f"  - {name}: {count:,}" for name, count in region_counts.items()])
    lines.extend(
        [
            "",
            "INITIAL GENERATED OUTCOME SUMMARY (DESCRIPTIVE ONLY)",
            f"Late-shipment rate: {late_rate:.2f}%",
            f"Mean actual delivery duration: {df['actual_delivery_days'].mean():.2f} days",
            f"Median actual delivery duration: {df['actual_delivery_days'].median():.2f} days",
            f"Mean transportation cost: INR {df['transportation_cost_inr'].mean():.2f}",
            "",
            "INTERPRETATION LIMITATIONS",
            "- These results describe the simulation assumptions, not real operations.",
            "- Relationships may partly reflect the formulas used to generate the data.",
            "- Correlation does not establish real-world causation.",
            "- Any recommendations must be labelled as illustrative and require validation",
            "  using actual company shipment, carrier, route and cost data.",
        ]
    )
    ASSUMPTIONS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("WEEK 3 — HYPOTHETICAL LOGISTICS DATASET GENERATION")
    print("=" * 72)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Output folder: {OUTPUT_DIR}")
    print(f"Rows requested: {N_SHIPMENTS:,}")
    print(f"Random seed: {RANDOM_SEED}")

    df = generate_dataset()
    validate_dataset(df)

    profile = create_profile(df)
    dictionary = create_dictionary()

    df.to_csv(DATA_PATH, index=False, encoding="utf-8")
    profile.to_csv(PROFILE_PATH, index=False, encoding="utf-8")
    dictionary.to_csv(DICTIONARY_PATH, index=False, encoding="utf-8")
    write_assumptions(df)

    print("\nDATASET VALIDATION")
    print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"Unique shipment IDs: {df['shipment_id'].nunique():,}")
    print(f"Exact duplicate rows: {df.duplicated().sum():,}")
    print(f"Missing cells: {int(df.isna().sum().sum()):,}")
    print(f"Negative schedule variance records: {(df['schedule_variance_days'] < 0).sum():,}")
    print(f"Late shipments: {int(df['late_delivery'].sum()):,} ({df['late_delivery'].mean() * 100:.2f}%)")
    print(f"Mean actual delivery time: {df['actual_delivery_days'].mean():.2f} days")
    print(f"Median actual delivery time: {df['actual_delivery_days'].median():.2f} days")
    print(f"Mean transportation cost: INR {df['transportation_cost_inr'].mean():,.2f}")
    print("\nCREATED FILES")
    for path in [DATA_PATH, PROFILE_PATH, DICTIONARY_PATH, ASSUMPTIONS_PATH]:
        print(f"{path.relative_to(PROJECT_ROOT)} ({path.stat().st_size:,} bytes)")

    print("\nAll generation checks passed. The dataset is synthetic and reproducible.")
    print("No Week 1 or Week 2 files were modified.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # Show a useful message if a generation/validation step fails.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
