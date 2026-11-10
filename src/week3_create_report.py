
from pathlib import Path
import pandas as pd

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ============================================================
# PATHS AND INPUTS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"
REPORTS = ROOT / "report"

REPORTS.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = REPORTS / "Logistics_Data_Analysis_Visualization_Week3_Report.docx"

FILES = {
    "kpi": "week3_eda_kpi_summary.csv",
    "descriptive": "week3_eda_descriptive_statistics.csv",
    "mode": "week3_deep_dive_by_service_mode.csv",
    "region": "week3_deep_dive_by_region.csv",
    "monthly": "week3_eda_monthly_trends.csv",
    "quarterly": "week3_deep_dive_quarterly.csv",
    "peak": "week3_deep_dive_peak_period_comparison.csv",
    "outliers": "week3_eda_iqr_outlier_review.csv",
    "correlations": "week3_deep_dive_correlation_pairs.csv",
    "validation": "week3_deep_dive_validation.csv",
    "outcomes": "week3_deep_dive_delivery_outcomes.csv",
    "cost": "week3_deep_dive_cost_efficiency.csv",
    "percentiles": "week3_deep_dive_percentiles.csv",
    "dictionary": "week3_dataset_dictionary.csv",
}

CHARTS_LIST = [
    (
        "WEEK3_01_delivery_outcomes.png",
        "Figure 1. Shipment delivery outcomes",
        "The chart separates shipments delivered early, exactly on schedule and late. "
        "It shows 71.40% early deliveries, 0.84% exactly on schedule and 27.76% late deliveries. "
        "This provides an overall view of service performance against promised dates."
    ),
    (
        "WEEK3_02_late_rate_by_shipping_mode.png",
        "Figure 2. Late-delivery rate by shipping mode",
        "Express has the highest observed late rate (40.65%), followed by Standard (26.20%) "
        "and Economy (18.07%). The service-mode comparison should be interpreted alongside "
        "promised delivery windows and actual delivery durations."
    ),
    (
        "WEEK3_03_late_rate_by_region.png",
        "Figure 3. Late-delivery rate by simulated region",
        "East records the highest late rate (35.69%), while North records the lowest (21.53%). "
        "This identifies regions that would merit closer investigation in a real operation."
    ),
    (
        "WEEK3_04_monthly_volume_and_late_rate.png",
        "Figure 4. Monthly shipment volume and late-delivery rate",
        "The combined chart compares shipment volume with the monthly late-delivery rate. "
        "The late rate rises in the final quarter, reaching 40.14% in December. "
        "The two axes represent different measures and should be read independently."
    ),
    (
        "WEEK3_05_actual_vs_promised_delivery.png",
        "Figure 5. Actual versus promised delivery time",
        "Each point represents a simulated shipment. The diagonal reference line represents "
        "actual delivery time equal to promised delivery time. Points above the line indicate "
        "late deliveries; points below the line indicate early deliveries."
    ),
    (
        "WEEK3_06_distance_vs_cost.png",
        "Figure 6. Shipment distance and transportation cost",
        "The scatter plot shows a strong positive monotonic association between distance and "
        "transportation cost (Spearman rho = 0.811). Longer simulated journeys generally have "
        "higher transportation costs. This association is partly built into the simulation formula."
    ),
    (
        "WEEK3_07_transportation_cost_distribution.png",
        "Figure 7. Distribution of transportation costs",
        "The distribution is right-skewed: most shipments fall in the lower-to-middle cost "
        "range, while a smaller number of shipments have substantially higher costs. "
        "The mean (INR 933.03) exceeds the median (approximately INR 836.09), reflecting the "
        "influence of higher-cost shipments."
    ),
    (
        "WEEK3_08_spearman_correlation_heatmap.png",
        "Figure 8. Spearman correlation heatmap",
        "The heatmap summarises monotonic relationships among numerical operational variables. "
        "Notable associations include fuel surcharge with total transportation cost (rho = 0.941), "
        "distance with fuel surcharge (rho = 0.898), and promised with actual delivery time "
        "(rho = 0.862). These are associations, not proof of causation."
    ),
    (
        "WEEK3_09_delivery_time_by_shipping_mode.png",
        "Figure 9. Actual delivery-time distribution by shipping mode",
        "The box plot compares the median, interquartile range and spread of actual delivery "
        "times across the three service modes. Express has the lowest median delivery time, "
        "while Economy has the highest. This complements the late-rate comparison."
    ),
]

CHART_RATIONALES = {
    "WEEK3_01_delivery_outcomes.png":
        "A bar chart is suitable for comparing shipment counts across "
        "three discrete delivery-outcome categories.",

    "WEEK3_02_late_rate_by_shipping_mode.png":
        "A bar chart makes late-delivery percentages directly comparable "
        "across the three service modes. Sample sizes are included for context.",

    "WEEK3_03_late_rate_by_region.png":
        "A bar chart provides a clear ranking of regional late-delivery rates "
        "on a common percentage scale.",

    "WEEK3_04_monthly_volume_and_late_rate.png":
        "A combination chart uses bars for monthly shipment volume and a line "
        "for late-delivery rate, allowing two different time-based measures "
        "to be examined together using separate axes.",

    "WEEK3_05_actual_vs_promised_delivery.png":
        "A scatter plot is appropriate for two continuous variables. "
        "The equality line helps distinguish early and late deliveries.",

    "WEEK3_06_distance_vs_cost.png":
        "A scatter plot shows the relationship between two numerical variables "
        "and helps reveal patterns, spread and unusual observations.",

    "WEEK3_07_transportation_cost_distribution.png":
        "A histogram shows the shape, concentration and skewness of the "
        "transportation-cost distribution. Mean and median markers aid comparison.",

    "WEEK3_08_spearman_correlation_heatmap.png":
        "A heatmap presents the correlation matrix compactly, allowing the "
        "direction and strength of multiple numerical relationships to be compared.",

    "WEEK3_09_delivery_time_by_shipping_mode.png":
        "A box plot compares the median, interquartile range and spread of "
        "delivery times across multiple categorical groups."
}

# ============================================================
# LOAD AND VALIDATE INPUTS
# ============================================================

def load_csv(key):
    path = DATA / FILES[key]
    if not path.exists():
        raise FileNotFoundError(f"Required input file is missing: {path}")
    return pd.read_csv(path)


tables = {key: load_csv(key) for key in FILES}

dataset_path = DATA / "week3_simulated_logistics.csv"
assumptions_path = DATA / "week3_simulation_assumptions.txt"

if not dataset_path.exists():
    raise FileNotFoundError(f"Missing simulated dataset: {dataset_path}")

if not assumptions_path.exists():
    raise FileNotFoundError(f"Missing simulation notes: {assumptions_path}")

df = pd.read_csv(dataset_path, low_memory=False)

if len(df) != 5000:
    raise ValueError(f"Expected 5,000 shipments; found {len(df):,}")

if df["shipment_id"].nunique() != len(df):
    raise ValueError("Shipment IDs are not unique. Resolve this before reporting.")

if df.isna().sum().sum() != 0:
    raise ValueError("The simulated dataset contains missing values.")

if not (df["late_delivery"] == (
    df["schedule_variance_days"] > 0
).astype(int)).all():
    raise ValueError("Late-delivery labels do not match the documented rule.")


# ============================================================
# DOCUMENT DESIGN HELPERS
# ============================================================

doc = Document()

section = doc.sections[0]
section.top_margin = Inches(0.72)
section.bottom_margin = Inches(0.72)
section.left_margin = Inches(0.78)
section.right_margin = Inches(0.78)

NAVY = "16324F"
BLUE = "245B83"
LIGHT_BLUE = "EAF1F7"
PALE = "F4F7FA"
DARK = "243447"
GREY = "64748B"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=DARK, size=8.5):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(2)
    run = paragraph.add_run(str(text))
    run.bold = bold
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(dataframe, columns=None, headers=None, max_rows=None, font_size=8):
    if dataframe is None or dataframe.empty:
        doc.add_paragraph("No table data available.")
        return

    data = dataframe.copy()

    if columns:
        available = [c for c in columns if c in data.columns]
        data = data[available]

    if max_rows is not None:
        data = data.head(max_rows)

    if headers is None:
        headers = list(data.columns)

    table = doc.add_table(rows=1, cols=len(data.columns))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True

    for i, heading in enumerate(headers):
        set_cell_text(table.rows[0].cells[i], heading, True, WHITE, font_size)
        set_cell_shading(table.rows[0].cells[i], NAVY)

    for _, row in data.iterrows():
        cells = table.add_row().cells

        for i, value in enumerate(row.tolist()):
            if pd.isna(value):
                display = "—"

            elif isinstance(value, (int, float)):
                numeric_value = float(value)

                if numeric_value.is_integer():
                    display = f"{numeric_value:,.0f}"
                else:
                    display = f"{numeric_value:,.3f}"

            else:
                display = str(value)

            set_cell_text(cells[i], display, False, DARK, font_size)


    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_heading(text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(5)
    return p


def add_body(text, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.08

    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text[len(bold_prefix):])
    else:
        p.add_run(text)
    return p


def add_bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.add_run(text)
    return p


NUMBER_COUNTER = 0

def add_number(text):
    global NUMBER_COUNTER
    NUMBER_COUNTER += 1

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.space_after = Pt(3)

    number = p.add_run(f"{NUMBER_COUNTER}. ")
    number.bold = True
    p.add_run(text)

    return p


def add_code(text):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F1F4F7")
    cell.text = ""

    for index, line in enumerate(text.strip("\n").splitlines()):
        p = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(line if line else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(7.5)
        run.font.color.rgb = RGBColor.from_string("263445")

    doc.add_paragraph().paragraph_format.space_after = Pt(1)



def add_chart(filename, caption, interpretation):
    path = CHARTS / filename

    if not path.exists():
        add_body(f"Chart unavailable: {filename}")
        return

    # Insert and centre the chart image
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.add_run().add_picture(str(path), width=Inches(6.25))

    # Add the chart caption
    cap = doc.add_paragraph()
    cap.paragraph_format.keep_with_next = True
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(3)

    r = cap.add_run(caption)
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor.from_string(BLUE)

    # Explain why this chart type was selected
    rationale = CHART_RATIONALES.get(filename)

    if rationale:
        why = doc.add_paragraph()
        why.paragraph_format.keep_with_next = True
        why.paragraph_format.space_after = Pt(3)
        why.paragraph_format.left_indent = Inches(0.18)
        why.paragraph_format.right_indent = Inches(0.18)

        why.add_run("Chart choice: ").bold = True
        why.add_run(rationale)

    # Add the analytical interpretation
    note = doc.add_paragraph()
    note.paragraph_format.space_after = Pt(10)
    note.paragraph_format.left_indent = Inches(0.18)
    note.paragraph_format.right_indent = Inches(0.18)

    note.add_run("Interpretation: ").bold = True
    note.add_run(interpretation)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor.from_string(GREY)

    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    paragraph._p.append(field)


def get_kpi(metric):
    data = tables["kpi"]
    row = data.loc[data["Metric"] == metric, "Value"]
    if row.empty:
        raise ValueError(f"Missing KPI in summary file: {metric}")
    return float(row.iloc[0])


def inr(value):
    return f"INR {value:,.2f}"


# ============================================================
# DOCUMENT STYLES, HEADER AND FOOTER
# ============================================================

styles = doc.styles
styles["Normal"].font.name = "Arial"
styles["Normal"].font.size = Pt(9.5)
styles["Normal"].font.color.rgb = RGBColor.from_string(DARK)

for style_name, size, color in [
    ("Title", 28, NAVY),
    ("Heading 1", 17, NAVY),
    ("Heading 2", 12, BLUE),
    ("Heading 3", 10, DARK),
]:
    style = styles[style_name]
    style.font.name = "Arial"
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = RGBColor.from_string(color)

header = section.header.paragraphs[0]
header.text = "YUVAINTERN  |  LOGISTICS DATA ANALYST INTERNSHIP  |  WEEK 3"
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
for run in header.runs:
    run.font.name = "Arial"
    run.font.size = Pt(7.5)
    run.font.color.rgb = RGBColor.from_string(GREY)

footer = section.footer.paragraphs[0]
add_page_number(footer)


# ============================================================
# COVER PAGE
# ============================================================

cover = doc.add_paragraph()
cover.paragraph_format.space_before = Pt(75)
cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = cover.add_run("LOGISTICS DATA ANALYTICS")
run.bold = True
run.font.name = "Arial"
run.font.size = Pt(27)
run.font.color.rgb = RGBColor.from_string(NAVY)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Advanced Data Analysis and Visualization")
r.bold = True
r.font.size = Pt(18)
r.font.color.rgb = RGBColor.from_string(BLUE)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("WEEK 3 PROJECT REPORT")
r.bold = True
r.font.size = Pt(13)
r.font.color.rgb = RGBColor.from_string(GREY)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("A reproducible exploratory analysis of a hypothetical logistics operation").italic = True

doc.add_paragraph()
for line in [
    "Prepared by: Pravallika Gurubhagatavula",
    "Programme: Logistics Data Analyst Intern",
    "Organisation: YuvaIntern",
    "Analysis period represented: January–December 2025",
    "Dataset: 5,000 synthetic shipment records",
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(line)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("IMPORTANT DATA NOTE")
r.bold = True
r.font.color.rgb = RGBColor.from_string(BLUE)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.left_indent = Inches(0.7)
p.paragraph_format.right_indent = Inches(0.7)
p.add_run(
    "All shipment records and results in this report are synthetic and were generated "
    "for an educational assignment. They do not represent a real company or actual "
    "logistics operations."
)

doc.add_page_break()


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

add_heading("Executive Summary", 1)

add_body(
    "This project explores a hypothetical logistics operation using a reproducible "
    "dataset of 5,000 synthetic shipments and 16 variables. The analysis examines "
    "delivery outcomes, service-mode performance, regional differences, monthly and "
    "quarterly patterns, transportation costs, numerical distributions and correlations."
)

add_body(
    "The dataset contains no missing cells, exact duplicate rows or duplicate shipment "
    "identifiers. The late-delivery indicator was independently checked against the "
    "documented rule: a shipment is late when actual delivery time exceeds promised "
    "delivery time."
)

add_body(
    f"The simulated late-delivery rate is {get_kpi('Late shipment rate'):.2f}%. "
    f"Express has the highest late rate at 40.65%, even though it has the shortest "
    "mean actual delivery time. The East region has the highest regional late rate "
    "at 35.69%. The Q4 late rate is 37.36%, compared with 24.56% for January–September."
)

add_body(
    f"Mean transportation cost is {inr(get_kpi('Mean transportation cost'))} "
    f"per shipment, while the median is {inr(get_kpi('Median transportation cost'))}. "
    "The difference indicates a right-skewed cost distribution."
)

add_body(
    "These results demonstrate how exploratory analysis can help identify operational "
    "segments that deserve further investigation. Because the dataset is synthetic and "
    "some relationships are embedded in its generation formulas, the findings are "
    "illustrative rather than evidence about real logistics operations."
)

add_heading("Key Results at a Glance", 2)
kpi_cards = pd.DataFrame([
    ["Shipments analysed", f"{len(df):,}", "shipments"],
    ["Late shipments", f"{int(df['late_delivery'].sum()):,}", "shipments"],
    ["Late-delivery rate", f"{df['late_delivery'].mean() * 100:.2f}", "%"],
    ["Mean actual delivery time", f"{df['actual_delivery_days'].mean():.2f}", "days"],
    ["Mean transportation cost", f"{inr(df['transportation_cost_inr'].mean())}", "per shipment"],
    ["Mean schedule variance", f"{df['schedule_variance_days'].mean():.3f}", "days"],
], columns=["Measure", "Result", "Unit"])
add_table(kpi_cards, headers=["Measure", "Result", "Unit"], font_size=8.5)


# ============================================================
# CONTENTS
# ============================================================

add_heading("Report Contents", 1)
for item in [
    "1. Project Background and Objectives",
    "2. Dataset Design and Simulation Assumptions",
    "3. Analytical Methodology and Validation",
    "4. Key Performance Indicators",
    "5. Exploratory Data Analysis",
    "6. Visual Analysis and Interpretation",
    "7. Operational Insights and Recommendations",
    "8. Limitations and Responsible Interpretation",
    "9. Conclusion",
    "Appendix A. Python Code Illustrations",
    "Appendix B. Dataset Dictionary",
    "Appendix C. Reproducibility and Project Files",
]:
    add_bullet(item)


# ============================================================
# 1. BACKGROUND AND OBJECTIVES
# ============================================================

add_heading("1. Project Background and Objectives", 1)

add_body(
    "Logistics operations involve decisions about delivery promises, service modes, "
    "geographic coverage, shipment handling and transportation expenditure. "
    "Exploratory data analysis helps transform shipment-level records into summaries "
    "that can guide operational questions."
)

add_heading("1.1 Business Scenario", 2)
add_body(
    "The hypothetical organisation in this project manages shipments across five "
    "simulated regions using Economy, Standard and Express service modes. Each shipment "
    "has a distance, weight, volume, dispatch delay, disruption index, handling time, "
    "promised delivery duration, actual delivery duration and transportation cost."
)

NUMBER_COUNTER = 0
add_heading("1.2 Project Objectives", 2)
for item in [
    "Generate a documented and reproducible hypothetical logistics dataset.",
    "Validate dataset structure, identifiers, missing values and delivery calculations.",
    "Summarise central tendency, spread, skewness and percentile behaviour.",
    "Compare delivery performance across service modes and regions.",
    "Explore monthly and quarterly patterns in shipment volume and late deliveries.",
    "Examine relationships between distance, weight, delivery duration and cost.",
    "Create visualisations that communicate operational patterns clearly.",
    "Develop cautious, evidence-based recommendations for further operational investigation.",
]:
    add_number(item)


# ============================================================
# 2. DATASET AND SIMULATION
# ============================================================

add_heading("2. Dataset Design and Simulation Assumptions", 1)

add_body(
    "The dataset was generated locally using Python and a fixed random seed. "
    "A fixed seed makes the simulation reproducible: repeated execution with the same "
    "script and environment produces the same generated records."
)

add_heading("2.1 Dataset Profile", 2)
profile = pd.DataFrame([
    ["Records", f"{len(df):,}"],
    ["Variables", f"{df.shape[1]}"],
    ["Unique shipment identifiers", f"{df['shipment_id'].nunique():,}"],
    ["Date coverage", f"{df['order_date'].min()} to {df['order_date'].max()}"],
    ["Regions", f"{df['region'].nunique()}"],
    ["Shipping modes", f"{df['shipping_mode'].nunique()}"],
    ["Missing cells", f"{int(df.isna().sum().sum()):,}"],
    ["Exact duplicate rows", f"{int(df.duplicated().sum()):,}"],
], columns=["Dataset characteristic", "Value"])
add_table(profile, font_size=8.5)

add_heading("2.2 Variable Groups", 2)
add_body(
    "The 16 variables can be grouped into shipment identification and context, "
    "operational inputs, delivery performance and transportation cost."
)
for item in [
    "Shipment context: shipment_id, order_date, region and shipping_mode.",
    "Shipment attributes: distance_km, shipment_weight_kg and shipment_volume_m3.",
    "Operational factors: dispatch_delay_hours, disruption_index and handling_time_hours.",
    "Delivery measures: promised_delivery_days, actual_delivery_days, "
    "schedule_variance_days and late_delivery.",
    "Cost measures: fuel_surcharge_inr and transportation_cost_inr.",
]:
    add_bullet(item)

add_heading("2.3 Simulation Assumptions", 2)
add_body(
    "Distance, weight and volume were generated from bounded distributions. "
    "Promised delivery time was based partly on distance and service-mode assumptions. "
    "Actual delivery time included simulated operational delays, handling, disruption, "
    "regional and peak-period adjustments, and random variation. Transportation cost "
    "was generated from distance, shipment attributes, service-mode factors and a fuel "
    "surcharge component."
)
add_body(
    "The simulation notes are retained in data/processed/week3_simulation_assumptions.txt. "
    "They should be treated as part of the analytical evidence because they describe "
    "how the dataset was constructed."
)


# ============================================================
# 3. METHODOLOGY AND VALIDATION
# ============================================================

add_heading("3. Analytical Methodology and Validation", 1)

NUMBER_COUNTER = 0
add_heading("3.1 Analysis Workflow", 2)
for item in [
    "Generate the hypothetical dataset using a fixed random seed.",
    "Load the CSV using pandas and inspect dimensions, data types and sample records.",
    "Check missing values, duplicates, unique identifiers and invalid values.",
    "Reconcile schedule variance with actual delivery time minus promised delivery time.",
    "Validate the late-delivery indicator against the documented positive-variance rule.",
    "Calculate descriptive statistics and grouped performance summaries.",
    "Calculate Pearson and Spearman correlations for numerical variables.",
    "Create charts and export analysis tables for reporting.",
    "Interpret findings while keeping simulation limitations explicit.",
]:
    add_number(item)

add_heading("3.2 Data Validation Results", 2)
validation = tables["validation"]
add_table(
    validation,
    columns=["Validation Check", "Result"],
    headers=["Validation check", "Observed result"],
    font_size=8
)

add_body(
    "The maximum reconciliation difference between the stored schedule variance "
    "and the recalculated value is effectively zero, allowing for floating-point "
    "precision. No invalid dates, negative distances or negative transportation costs "
    "were identified."
)

add_heading("3.3 Delivery Outcome Definition", 2)
add_body(
    "Schedule variance is calculated as actual delivery days minus promised delivery "
    "days. A negative value means the shipment arrived early; zero means it arrived "
    "exactly on schedule; a positive value means it arrived late."
)
add_code(
    'schedule_variance_days = actual_delivery_days - promised_delivery_days\n'
    'late_delivery = 1 if schedule_variance_days > 0 else 0'
)
add_body(
    "This definition matters because early shipments must not be counted as on-time "
    "shipments, and exactly-on-schedule shipments are a separate outcome."
)


# ============================================================
# 4. KPI DEFINITIONS
# ============================================================

add_heading("4. Key Performance Indicators", 1)

add_body(
    "The following indicators provide a consistent framework for evaluating the "
    "simulated operation."
)

kpi_definitions = pd.DataFrame([
    [
        "Late-delivery rate",
        "Late shipments / total shipments × 100",
        "Measures the share of shipments exceeding the promise."
    ],
    [
        "Early-delivery rate",
        "Early shipments / total shipments × 100",
        "Measures the share arriving before the promise."
    ],
    [
        "Exactly-on-schedule rate",
        "Shipments with zero schedule variance / total × 100",
        "Measures exact adherence to the promised duration."
    ],
    [
        "Mean actual delivery time",
        "Average actual_delivery_days",
        "Summarises average elapsed delivery time."
    ],
    [
        "Mean schedule variance",
        "Average(actual − promised)",
        "Negative values indicate average early delivery."
    ],
    [
        "Mean transportation cost",
        "Average transportation_cost_inr",
        "Summarises average shipment-level cost."
    ],
    [
        "Mean shipment-level cost per kilometre",
        "Mean(transportation_cost_inr / distance_km)",
        "Arithmetic average of individual shipment cost-per-km ratios."
    ],
    [
        "Weighted aggregate cost per kilometre",
        "Total transportation cost / total distance",
        "Aggregate cost per kilometre, weighted by shipment distance."
    ],
], columns=["KPI", "Calculation", "Interpretation"])

add_heading("4.1 Overall KPI Results", 2)
add_table(tables["kpi"], columns=["Metric", "Value", "Unit"], font_size=8)

add_body(
    "The mean schedule variance is approximately -0.165 days. Since schedule variance "
    "equals actual minus promised delivery duration, a negative mean indicates that "
    "the average shipment in this simulation arrived before its promised duration. "
    "It does not mean that every shipment was early: 1,388 shipments were classified late."
)

add_heading("4.2 Cost Efficiency: Two Complementary Measures", 2)

add_body(
    "Two different cost-per-kilometre measures are reported. "
    "The mean shipment-level ratio is the arithmetic average of each "
    "shipment's transportation cost divided by its distance. "
    "The weighted aggregate ratio divides total transportation cost "
    "by total shipment distance. They answer different questions and "
    "should not be treated as interchangeable."
)

add_table(
    tables["cost"],
    columns=["Metric", "Value"],
    headers=["Cost-efficiency measure", "Value (INR/km)"],
    font_size=8.5
)


# ============================================================
# 5. EXPLORATORY DATA ANALYSIS
# ============================================================

add_heading("5. Exploratory Data Analysis", 1)

add_heading("5.1 Central Tendency, Dispersion and Shape", 2)
add_body(
    "Mean and median are used together because a mean can be influenced by unusually "
    "large observations. Standard deviation and quartiles describe spread, while "
    "skewness provides an indication of asymmetry."
)

desc = tables["descriptive"].copy()

display_names = {
    "distance_km": "Distance (km)",
    "shipment_weight_kg": "Weight (kg)",
    "shipment_volume_m3": "Volume (m3)",
    "dispatch_delay_hours": "Dispatch delay (hours)",
    "disruption_index": "Disruption index",
    "handling_time_hours": "Handling time (hours)",
    "promised_delivery_days": "Promised delivery (days)",
    "actual_delivery_days": "Actual delivery (days)",
    "schedule_variance_days": "Schedule variance (days)",
    "fuel_surcharge_inr": "Fuel surcharge (INR)",
    "transportation_cost_inr": "Transport cost (INR)"
}

desc["Variable"] = (
    desc["Variable"].map(display_names)
    .fillna(desc["Variable"])
)

desc_columns = [
    "Variable", "Mean", "Median", "Standard Deviation",
    "Q1", "Q3", "Maximum", "Skewness"
]
add_table(desc, columns=desc_columns, font_size=7)

add_body(
    "The distribution of shipment weight, volume, distance, actual delivery time and "
    "transportation cost is positively skewed to varying degrees. In particular, "
    "shipment weight has a skewness of 3.213 and volume has a skewness of 2.727. "
    "For these variables, the median and upper percentiles provide useful context "
    "alongside the mean."
)

add_heading("5.2 Service-Mode Comparison", 2)
mode = tables["mode"]
add_table(
    mode,
    columns=[
        "shipping_mode", "Shipments", "Late_Shipments", "Late_Rate_pct",
        "Mean_Actual_Delivery_Days", "Mean_Promised_Delivery_Days",
        "Mean_Transportation_Cost_INR"
    ],
    headers=[
        "Service mode", "Shipments", "Late", "Late rate (%)",
        "Mean actual (days)", "Mean promise (days)", "Mean cost (INR)"
    ],
    font_size=7
)

add_body(
    "Express has the shortest mean actual delivery time (1.351 days), but also the "
    "highest late rate (40.65%). Its mean promised delivery duration is 1.407 days, "
    "shorter than the corresponding values for Standard and Economy. This suggests "
    "that the delivery promise is an important part of service performance: a service "
    "can be faster in absolute time while still missing its tighter promise more often."
)

add_heading("5.3 Regional Comparison", 2)
region = tables["region"]
add_table(
    region,
    columns=[
        "region", "Shipments", "Late_Shipments", "Late_Rate_pct",
        "Mean_Actual_Delivery_Days", "Mean_Transportation_Cost_INR"
    ],
    headers=[
        "Region", "Shipments", "Late", "Late rate (%)",
        "Mean actual (days)", "Mean cost (INR)"
    ],
    font_size=7.5
)

add_body(
    "East has the highest simulated late rate (35.69%), followed by Central (31.35%). "
    "North has the lowest late rate (21.53%). The difference between East and North "
    "is approximately 14.16 percentage points. In an actual operation, this pattern "
    "would justify investigation of routes, carrier performance, dispatch processes "
    "and regional operating conditions."
)

add_heading("5.4 Monthly and Quarterly Patterns", 2)
monthly = tables["monthly"]
add_table(
    monthly,
    columns=[
        "order_month", "Shipments", "Late_Shipments", "Late_Rate_pct",
        "Mean_Actual_Delivery_Days", "Mean_Transportation_Cost_INR"
    ],
    headers=[
        "Month", "Shipments", "Late", "Late rate (%)",
        "Mean actual (days)", "Mean cost (INR)"
    ],
    font_size=7
)

add_heading("Quarterly comparison", 3)
quarterly = tables["quarterly"]
add_table(
    quarterly,
    columns=[
        "quarter", "Shipments", "Late_Shipments", "Late_Rate_pct",
        "Mean_Actual_Delivery_Days", "Mean_Transportation_Cost_INR"
    ],
    headers=[
        "Quarter", "Shipments", "Late", "Late rate (%)",
        "Mean actual (days)", "Mean cost (INR)"
    ],
    font_size=7.5
)

add_body(
    "The Q4 late rate is 37.36%, compared with 24.56% for January–September. "
    "The difference is 12.80 percentage points. The simulation assumptions explicitly "
    "include a small October–December peak-period pressure adjustment. Therefore, this "
    "pattern demonstrates how the simulated peak-period factor appears in the output; "
    "it must not be presented as independently discovered real-world seasonality."
)

add_heading("5.5 Outlier Review", 2)
outliers = tables["outliers"]
add_table(
    outliers,
    columns=[
        "Variable", "Flagged_Records", "Flagged_Percent",
        "Lower_Fence", "Upper_Fence"
    ],
    headers=[
        "Variable", "Flagged records", "Flagged (%)",
        "Lower IQR fence", "Upper IQR fence"
    ],
    font_size=7
)

add_body(
    "The interquartile range method flags observations outside Q1 − 1.5 × IQR "
    "or Q3 + 1.5 × IQR. A flagged observation is not automatically an error. "
    "For example, a large shipment or high-cost long-distance shipment may be valid. "
    "The analysis therefore retains the records and treats the flags as prompts for "
    "business review rather than deletion instructions."
)

add_heading("5.6 Correlation Analysis", 2)
correlations = tables["correlations"]
add_table(
    correlations,
    columns=["Variable_1", "Variable_2", "Pearson_r", "Spearman_rho"],
    headers=["Variable 1", "Variable 2", "Pearson r", "Spearman rho"],
    max_rows=12,
    font_size=7.5
)

add_body(
    "Pearson correlation measures linear association, while Spearman correlation "
    "measures monotonic association using ranked values. Spearman is useful when "
    "variables are skewed or when the relationship may not be well represented by "
    "a straight line. Neither measure establishes causality."
)

add_body(
    "The strongest displayed association is between fuel surcharge and total "
    "transportation cost (Spearman rho = 0.941). Distance and fuel surcharge also "
    "show a strong association (rho = 0.898). These results are consistent with the "
    "simulation's cost-generation structure, which explicitly uses distance and "
    "a fuel-surcharge component."
)


# ============================================================
# 6. VISUAL ANALYSIS
# ============================================================

add_heading("6. Visual Analysis and Interpretation", 1)

add_body(
    "The visualisations were selected to match the analytical question. Bar charts "
    "compare categories, a line chart displays change over time, scatter plots examine "
    "relationships between two numerical measures, a histogram displays a distribution, "
    "a heatmap summarises correlations, and a box plot compares distributions across groups."
)

for filename, caption, interpretation in CHARTS_LIST:
    add_chart(filename, caption, interpretation)


# ============================================================
# 7. INSIGHTS AND RECOMMENDATIONS
# ============================================================

add_heading("7. Operational Insights and Recommendations", 1)

add_heading("7.1 Priority Findings", 2)
for item in [
    "Service-mode performance requires a promise-aware comparison. Express is fastest "
    "on average but has the highest late rate. Review whether the promised Express "
    "delivery windows are realistic for the simulated operating conditions.",

    "The East region has the highest late rate. In a real setting, review route-level "
    "performance, dispatch cut-off times, carrier hand-offs and local disruption records.",

    "The Q4 late rate is notably higher than the January–September rate. Since the "
    "simulation intentionally includes a peak-period adjustment, the result is a useful "
    "demonstration of peak-period analysis, not independent evidence of a seasonal effect.",

    "Transportation cost is strongly associated with distance and fuel surcharge in "
    "the simulation. Cost-control analysis should therefore distinguish distance-driven "
    "cost from other cost components.",

    "The cost distribution is right-skewed. Reporting both mean and median avoids "
    "allowing a small number of high-cost shipments to obscure the typical shipment."
]:
    add_bullet(item)

NUMBER_COUNTER = 0
add_heading("7.2 Recommended Follow-up Analyses", 2)
for item in [
    "Break regional results down by individual routes, carriers and shipment service levels.",
    "Compare late rates with sample sizes and confidence intervals before prioritising real interventions.",
    "Separate the effects of distance, shipment weight, volume and fuel surcharge in a cost model.",
    "Investigate high-cost records using shipment-level details rather than deleting statistical outliers.",
    "For peak planning, compare multiple years of actual operational data and account for changes in shipment mix.",
    "In future predictive work, use only features that would genuinely be available at the time a prediction is made."
]:
    add_number(item)

add_heading("7.3 Potential Management Actions", 2)

actions = pd.DataFrame([
    [
        "Express service",
        "40.65% late rate; mean delivery 1.351 days "
        "against a 1.407-day promise.",
        "Review route-level performance, dispatch cut-off "
        "times and the feasibility of Express delivery promises.",
        "Late-delivery rate; 90th-percentile schedule variance."
    ],
    [
        "East region",
        "35.69% late rate, compared with 21.53% in North.",
        "Investigate individual routes, carrier hand-offs, "
        "dispatch delays and disruption records.",
        "Regional late rate; route-level delivery performance."
    ],
    [
        "Q4 operations",
        "37.36% late rate versus 24.56% in January–September.",
        "Review capacity, staffing and shipment planning "
        "for peak-period demand.",
        "Monthly late rate; shipment volume; backlog."
    ],
    [
        "Transportation costs",
        "Spearman correlation of 0.941 between fuel surcharge "
        "and total transportation cost.",
        "Break down cost components and review high-cost "
        "shipments by distance, weight and service mode.",
        "Weighted cost per km; median shipment cost."
    ],
    [
        "High-cost shipments",
        "Mean cost INR 933.03 exceeds median cost INR 836.09.",
        "Examine high-percentile shipments to distinguish "
        "valid exceptional costs from possible inefficiencies.",
        "90th-percentile cost; cost per shipment."
    ],
], columns=[
    "Area",
    "Evidence from simulation",
    "Proposed management investigation",
    "KPI to monitor"
])

add_table(
    actions,
    headers=[
        "Area",
        "Evidence",
        "Recommended action",
        "Monitoring KPI"
    ],
    font_size=7
)

add_body(
    "These actions are proposed investigations rather than proven "
    "solutions. The findings originate from synthetic records. "
    "Any intervention should first be evaluated using actual "
    "shipment data and a suitable before-and-after comparison."
)


# ============================================================
# 8. LIMITATIONS
# ============================================================

add_heading("8. Limitations and Responsible Interpretation", 1)

for item in [
    "The dataset is synthetic. It does not describe real customers, carriers, shipments, routes or markets.",
    "Some relationships are embedded in the data-generation formulas. Correlations may therefore reflect the simulation design.",
    "The peak-period adjustment is an explicit simulation assumption, so the Q4 pattern is not independent evidence of real seasonality.",
    "The service modes and regions are hypothetical categories rather than validated operational geographies.",
    "The analysis is descriptive and exploratory. It does not estimate causal effects.",
    "Results from this dataset should not be used to set real delivery promises, carrier contracts or transportation budgets.",
    "Further work with timestamped operational records, carrier identifiers, route data, actual fuel prices and external disruption data would be needed for real-world validation."
]:
    add_bullet(item)

add_body(
    "These limitations do not invalidate the educational exercise. They define the "
    "scope in which its methods and findings can be interpreted responsibly."
)


# ============================================================
# 9. CONCLUSION
# ============================================================

add_heading("9. Conclusion", 1)

add_body(
    "This project completed an end-to-end exploratory analysis of a hypothetical "
    "logistics dataset containing 5,000 simulated shipments. The workflow included "
    "dataset generation, structural validation, KPI calculation, descriptive statistics, "
    "grouped comparisons, time-based analysis, outlier review, correlation analysis "
    "and visual communication."
)

add_body(
    "The most important simulated patterns were the elevated late-delivery rate for "
    "Express, the higher late rate in the East region and the Q4 increase in late "
    "deliveries. The cost analysis showed a right-skewed distribution and a strong "
    "monotonic association between distance and transportation cost."
)

add_body(
    "The project demonstrates how Python-based exploratory analysis can convert "
    "shipment-level data into structured operational evidence. The next stage should "
    "build on these findings with predictive modelling and optimisation, while "
    "preserving a clear distinction between simulation results and real-world evidence."
)


# ============================================================
# APPENDIX A — CODE ILLUSTRATIONS
# ============================================================

doc.add_page_break()
add_heading("Appendix A. Python Code Illustrations", 1)

add_body(
    "The following excerpts illustrate the main analytical operations used in the "
    "project. The complete executable implementations are maintained in the src folder."
)

add_heading("A.1 Load and inspect the simulated dataset", 2)
add_code(
    'import pandas as pd\n\n'
    'df = pd.read_csv("data/processed/week3_simulated_logistics.csv")\n'
    'print(df.shape)\n'
    'print(df.dtypes)\n'
    'print(df.isna().sum().sum())'
)

add_heading("A.2 Recalculate schedule variance and delivery outcome", 2)
add_code(
    'df["schedule_variance_days"] = (\n'
    '    df["actual_delivery_days"] - df["promised_delivery_days"]\n'
    ')\n\n'
    'df["late_delivery"] = (\n'
    '    df["schedule_variance_days"] > 0\n'
    ').astype(int)'
)

add_heading("A.3 Summarise performance by shipping mode", 2)
add_code(
    'mode_summary = df.groupby("shipping_mode").agg(\n'
    '    shipments=("shipment_id", "count"),\n'
    '    late_rate=("late_delivery", "mean"),\n'
    '    mean_delivery_days=("actual_delivery_days", "mean"),\n'
    '    mean_cost=("transportation_cost_inr", "mean")\n'
    ').reset_index()\n\n'
    'mode_summary["late_rate_pct"] = mode_summary["late_rate"] * 100'
)

add_heading("A.4 Calculate descriptive statistics and correlations", 2)
add_code(
    'numeric = df.select_dtypes(include="number")\n'
    'descriptive = numeric.describe().T\n\n'
    'pearson = numeric.corr(method="pearson")\n'
    'spearman = numeric.corr(method="spearman")'
)

add_heading("A.5 Generate a visual comparison", 2)
add_code(
    'import matplotlib.pyplot as plt\n\n'
    'mode_late = (\n'
    '    df.groupby("shipping_mode")["late_delivery"].mean() * 100\n'
    ')\n\n'
    'ax = mode_late.sort_values(ascending=False).plot(\n'
    '    kind="bar", figsize=(8, 5), title="Late rate by shipping mode"\n'
    ')\n'
    'ax.set_ylabel("Late shipments (%)")\n'
    'ax.set_xlabel("Shipping mode")\n'
    'plt.tight_layout()\n'
    'plt.savefig("outputs/charts/example_mode_comparison.png", dpi=200)\n'
    'plt.close()'
)

add_body(
    "The examples are concise excerpts for explanation. The full project scripts "
    "contain the complete generation, validation, tabulation and charting workflows."
)


# ============================================================
# APPENDIX B — DATA DICTIONARY
# ============================================================

add_heading("Appendix B. Dataset Dictionary", 1)
dictionary = tables["dictionary"]
add_table(
    dictionary,
    columns=["column", "definition", "type_or_unit"],
    headers=["Variable", "Definition", "Type / unit"],
    font_size=7.5
)


# ============================================================
# APPENDIX C — REPRODUCIBILITY
# ============================================================

add_heading("Appendix C. Reproducibility and Project Files", 1)

add_body(
    "The project is organised so that dataset generation, exploratory analysis, "
    "deep-dive analysis and report preparation can be run separately."
)

add_heading("C.1 Execution commands", 2)
add_code(
    'python src/week3_generate_dataset.py\n'
    'python src/week3_eda_analysis.py\n'
    'python src/week3_deep_dive_analysis.py\n'
    'python src/week3_create_report.py'
)

add_heading("C.2 Important project files", 2)
project_files = pd.DataFrame([
    ["src/week3_generate_dataset.py", "Creates the reproducible synthetic shipment dataset."],
    ["src/week3_eda_analysis.py", "Performs exploratory analysis and creates the nine charts."],
    ["src/week3_deep_dive_analysis.py", "Produces additional service, region, quarter, peak-period and cost summaries."],
    ["src/week3_create_report.py", "Builds this Word report from saved outputs."],
    ["data/processed/week3_simulated_logistics.csv", "The synthetic shipment-level dataset."],
    ["data/processed/week3_simulation_assumptions.txt", "Simulation assumptions and interpretation limitations."],
    ["data/processed/week3_dataset_dictionary.csv", "Variable definitions and units."],
    ["outputs/charts/WEEK3_*.png", "The nine generated report visualisations."],
], columns=["Project file", "Purpose"])
add_table(project_files, font_size=7.5)

add_body(
    "The synthetic dataset and report outputs are reproducible using the saved scripts "
    "and documented assumptions. Generated data should remain clearly labelled as synthetic."
)


# ============================================================
# FINAL DOCUMENT METADATA AND SAVE
# ============================================================

doc.core_properties.title = (
    "Logistics Data Analysis and Visualization — Week 3"
)
doc.core_properties.subject = (
    "Advanced exploratory data analysis and visualization in logistics"
)
doc.core_properties.author = "Pravallika Gurubhagatavula"
doc.core_properties.keywords = (
    "Logistics, Python, EDA, Data Analysis, Visualization, YuvaIntern"
)

doc.save(OUTPUT_FILE)

print("=" * 75)
print("WEEK 3 PROFESSIONAL REPORT CREATED")
print("=" * 75)
print(f"Report: {OUTPUT_FILE}")
print(f"Size: {OUTPUT_FILE.stat().st_size:,} bytes")
print(f"Dataset rows: {len(df):,}")
print(f"Dataset columns: {df.shape[1]}")
print(f"Charts expected: {len(CHARTS_LIST)}")
print(f"Charts found: {sum((CHARTS / item[0]).exists() for item in CHARTS_LIST)}")
print("Validation: passed")
print("Existing Week 1 and Week 2 reports were not modified.")
