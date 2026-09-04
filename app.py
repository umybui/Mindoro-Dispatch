import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_sortables import sort_items

# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="Mindoro Dispatch Dashboard",
    layout="wide"
)

st.title("Mindoro Dispatch Dashboard")

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data
def load_data():

    df = pd.read_excel(
        "Mindoro Dispatch Summary Final.xlsm",
        sheet_name="Main Query",
        engine="openpyxl"
    )

    df["Datetime"] = pd.to_datetime(
        df["Datetime"],
        errors="coerce"
    )

    df["Value"] = pd.to_numeric(
        df["Value"],
        errors="coerce"
    )

    return df

df = load_data()

# Optional manual refresh
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.success(
    f"Loaded {len(df):,} records"
)

df = df[df["Attribute"] == "NET MW"].copy()

df["Month"] = df["Datetime"].dt.month
df["Day"] = df["Datetime"].dt.day

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Filters")

# =====================================================
# AREA FILTER
# =====================================================

available_workbooks = sorted(
    df["SourceWorkbook"].dropna().unique()
)

workbook_map = {}

for wb in available_workbooks:

    if "Oriental" in str(wb):
        workbook_map[wb] = "Oriental Mindoro"

    elif "Occidental" in str(wb):
        workbook_map[wb] = "Occidental Mindoro"

    else:
        workbook_map[wb] = str(wb)

selected_workbooks = st.sidebar.multiselect(
    "Area",
    options=available_workbooks,
    default=available_workbooks,
    format_func=lambda x: workbook_map[x]
)

# =====================================================
# MONTH FILTER
# =====================================================

month_names = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec"
}

available_months = sorted(df["Month"].unique())

selected_months = st.sidebar.multiselect(
    "Month",
    options=available_months,
    default=available_months,
    format_func=lambda x: month_names[x]
)

# =====================================================
# DAY FILTER
# =====================================================

available_days = sorted(df["Day"].unique())

selected_days = st.sidebar.multiselect(
    "Day of Month",
    options=available_days,
    default=available_days
)

# =====================================================
# SHOW DEMAND
# =====================================================

show_demand = st.sidebar.checkbox(
    "Show Total Demand",
    value=True
)

# =====================================================
# FILTER DATA
# =====================================================

filtered = df[
    (df["SourceWorkbook"].isin(selected_workbooks))
    &
    (df["Month"].isin(selected_months))
    &
    (df["Day"].isin(selected_days))
].copy()

# =====================================================
# TOTAL DEMAND
# =====================================================

total_demand = (
    filtered[
        filtered["Plant"] == "TOTAL DEMAND"
    ]
    .groupby(
        "Datetime",
        as_index=False
    )["Value"]
    .sum()
)

# =====================================================
# GENERATION DATA
# =====================================================

generation = filtered[
    ~filtered["Plant"].isin([
        "TOTAL DEMAND",
        "TOTAL GENERATION DISPATCH",
        "SYNCHRO  \nEXPORT (-)  \nIMPORT (+)"
    ])
].copy()

# =====================================================
# TOTAL GENERATION
# =====================================================

total_generation = (
    generation
    .groupby(
        "Datetime",
        as_index=False
    )["Value"]
    .sum()
)

total_generation.rename(
    columns={
        "Value": "TotalGeneration"
    },
    inplace=True
)

# =====================================================
# KPI DATA
# =====================================================

gap_df = total_demand.merge(
    total_generation,
    on="Datetime",
    how="inner"
)

gap_df.rename(
    columns={
        "Value": "TotalDemand"
    },
    inplace=True
)

gap_df["ShortageMW"] = (
    gap_df["TotalDemand"]
    - gap_df["TotalGeneration"]
)

gap_df["ShortageArea"] = gap_df["ShortageMW"].clip(lower=0)

gap_df["ReserveMargin"] = (
    gap_df["TotalGeneration"]
    - gap_df["TotalDemand"]
)

peak_demand = gap_df["TotalDemand"].max()

peak_row = gap_df.loc[
    gap_df["TotalDemand"].idxmax()
]

peak_datetime = peak_row["Datetime"]

hours_with_shortage = (
    gap_df["ShortageMW"] > 0
).sum()

max_shortage = max(
    gap_df["ShortageMW"].max(),
    0
)

unserved_energy = (
    gap_df.loc[
        gap_df["ShortageMW"] > 0,
        "ShortageMW"
    ].sum()
)

hours_low_reserve = (
    gap_df["ReserveMargin"] < 5
).sum()

total_shortage_mwh = gap_df.loc[
    gap_df["ShortageMW"] > 0,
    "ShortageMW"
].sum()

# =====================================================
# INITIAL SORT
# =====================================================

sort_option = st.sidebar.selectbox(
    "Initial Order",
    [
        "Largest Generator First",
        "Alphabetical",
        "Smallest Generator First"
    ]
)

plant_stats = (
    generation
    .groupby("Plant")["Value"]
    .mean()
    .reset_index()
)

if sort_option == "Alphabetical":

    plant_order = sorted(
        generation["Plant"].unique()
    )

elif sort_option == "Largest Generator First":

    plant_order = (
        plant_stats
        .sort_values(
            "Value",
            ascending=False
        )["Plant"]
        .tolist()
    )

else:

    plant_order = (
        plant_stats
        .sort_values(
            "Value",
            ascending=True
        )["Plant"]
        .tolist()
    )

# =====================================================
# PLANT FILTER
# =====================================================

selected_plants = st.sidebar.multiselect(
    "Plants",
    options=plant_order,
    default=plant_order
)

generation = generation[
    generation["Plant"].isin(selected_plants)
]


# =====================================================
# KPI DISPLAY
# =====================================================

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "Peak Demand",
        f"{peak_demand:,.2f} MW"
    )

with k2:
    st.metric(
        "Maximum Shortage",
        f"{max_shortage:,.2f} MW"
    )

with k3:
    st.metric(
        "Unserved Energy",
        f"{unserved_energy:,.2f} MWh"
    )

with k4:
    st.metric(
        "Hours with Shortage",
        f"{hours_with_shortage:,}"
    )

with k5:
    st.metric(
        "Low Reserve Hours (<5 MW)",
        f"{hours_low_reserve:,}"
    )

with k6:
    st.metric(
        "Peak Demand Time",
        peak_datetime.strftime(
            "%Y-%m-%d %H:%M"
        )
    )

gap_df["MonthName"] = (
    gap_df["Datetime"]
    .dt.strftime("%b")
)

monthly_summary = (
    gap_df
    .groupby("MonthName")
    .agg(
        PeakDemand=("TotalDemand", "max"),
        MaxShortage=("ShortageMW", "max"),
        HoursWithShortage=(
            "ShortageMW",
            lambda x: (x > 0).sum()
        ),
        LowReserveHours=(
            "ReserveMargin",
            lambda x: (x < 5).sum()
        ),
        UnservedEnergy=(
            "ShortageMW",
            lambda x: x.clip(lower=0).sum()
        )
    )
    .reset_index()
)

st.caption("Monthly Performance Summary")

st.dataframe(
    monthly_summary,
    use_container_width=True,
    hide_index=True
)

# =====================================================
# BOXPLOTS
# =====================================================

st.subheader("Demand Distribution Analysis")

b1, b2 = st.columns(2)

# =====================================================
# CHART
# =====================================================

fig = go.Figure()

daily_peak = (
    total_demand.assign(
        Date=total_demand["Datetime"].dt.date,
        Month=total_demand["Datetime"].dt.strftime("%b")
    )
    .groupby(["Month", "Date"], as_index=False)
    .agg(
        DailyPeak=("Value", "max")
    )
)

month_order = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec"
]

fig_peak = go.Figure()

for month in month_order:

    temp = daily_peak[
        daily_peak["Month"] == month
    ]

    if len(temp) == 0:
        continue

    fig_peak.add_trace(
        go.Box(
            y=temp["DailyPeak"],
            name=month,
            boxmean=True
        )
    )

fig_peak.update_layout(
    title="Daily Peak Demand by Month",
    yaxis_title="MW",
    height=450
)

with b1:
    st.plotly_chart(
        fig_peak,
        use_container_width=True
    )

hourly_profile = total_demand.copy()

hourly_profile["Hour"] = (
    hourly_profile["Datetime"]
    .dt.hour
)

fig_hour = go.Figure()

for hr in range(24):

    temp = hourly_profile[
        hourly_profile["Hour"] == hr
    ]

    if len(temp) == 0:
        continue

    fig_hour.add_trace(
        go.Box(
            y=temp["Value"],
            name=str(hr),
            boxmean=True
        )
    )

fig_hour.update_layout(
    title="Hourly Demand Distribution",
    xaxis_title="Hour of Day",
    yaxis_title="MW",
    height=450
)

with b2:
    st.plotly_chart(
        fig_hour,
        use_container_width=True
    )

average_load = total_demand["Value"].mean()

load_factor = (
    average_load
    / peak_demand
    * 100
)

st.metric(
    "Load Factor",
    f"{load_factor:.1f}%"
)

# =====================================================
# LOAD DURATION CURVE SETTINGS
# =====================================================

st.sidebar.subheader("LDC Parameters")

peak_cutoff = st.sidebar.number_input(
    "Peak Region (%)",
    min_value=1,
    max_value=99,
    value=20,
    step=1
)

baseload_cutoff = st.sidebar.number_input(
    "Baseload Region Start (%)",
    min_value=1,
    max_value=99,
    value=80,
    step=1
)

fig_ldc.add_vline(
    x=peak_cutoff,
    line_dash="dot",
    line_color="red",
    annotation_text="Peak"
)

fig_ldc.add_vline(
    x=baseload_cutoff,
    line_dash="dot",
    line_color="green",
    annotation_text="Baseload"
)

# Peak Region

fig_ldc.add_vrect(
    x0=0,
    x1=peak_cutoff,
    fillcolor="red",
    opacity=0.08,
    line_width=0,
    annotation_text="Peak"
)

# Mid Merit

fig_ldc.add_vrect(
    x0=peak_cutoff,
    x1=baseload_cutoff,
    fillcolor="yellow",
    opacity=0.08,
    line_width=0,
    annotation_text="Mid-Merit"
)

# Baseload

fig_ldc.add_vrect(
    x0=baseload_cutoff,
    x1=100,
    fillcolor="green",
    opacity=0.08,
    line_width=0,
    annotation_text="Baseload"
)

# =====================================================
# LOAD DURATION CURVE
# =====================================================

st.subheader("Load Duration Curve")

ldc = (
    total_demand["Value"]
    .sort_values(ascending=False)
    .reset_index(drop=True)
)

ldc_pct = (
    (ldc.index + 1)
    / len(ldc)
    * 100
)

fig_ldc = go.Figure()

fig_ldc.add_trace(
    go.Scatter(
        x=ldc_pct,
        y=ldc,
        mode="lines",
        name="Demand",
        line=dict(
            color="black",
            width=3
        )
    )
)

average_load = total_demand["Value"].mean()

fig_ldc.add_hline(
    y=average_load,
    line_dash="dash",
    annotation_text=(
        f"Average Load "
        f"({average_load:,.2f} MW)"
    )
)

fig_ldc.update_layout(
    title="Load Duration Curve",
    xaxis_title="Percent of Time Exceeded (%)",
    yaxis_title="Demand (MW)",
    height=500,
    hovermode="x unified"
)

st.plotly_chart(
    fig_ldc,
    use_container_width=True
)



# -----------------------------------------------------
# GENERATION STACK
# -----------------------------------------------------

for plant in plant_order:

    if plant not in selected_plants:
        continue

    temp = generation[
        generation["Plant"] == plant
    ]

    fig.add_trace(
        go.Scatter(
            x=temp["Datetime"],
            y=temp["Value"],
            name=plant,
            mode="lines",
            stackgroup="generation"
        )
    )

# -----------------------------------------------------
# SHORTAGE CALCULATION
# -----------------------------------------------------

gap_df["ShortageArea"] = (
    gap_df["TotalDemand"]
    - gap_df["TotalGeneration"]
).clip(lower=0)

# -----------------------------------------------------
# ORANGE SHORTAGE SHADE
# -----------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=gap_df["Datetime"],
        y=gap_df["TotalGeneration"],
        mode="lines",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False
    )
)

fig.add_trace(
    go.Scatter(
        x=gap_df["Datetime"],
        y=gap_df["TotalGeneration"]
        + gap_df["ShortageArea"],
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(255,140,0,0.80)",
        line=dict(width=0),
        name="SHORTAGE",
        customdata=gap_df["ShortageArea"],
        hovertemplate=
            "SHORTAGE: %{customdata:.2f} MW"
            "<extra></extra>"
    )
)

# -----------------------------------------------------
# TOTAL GENERATION
# -----------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=total_generation["Datetime"],
        y=total_generation["TotalGeneration"],
        name="TOTAL GENERATION",
        mode="lines",
        line=dict(
            color="red",
            width=2
        )
    )
)

# -----------------------------------------------------
# TOTAL DEMAND
# -----------------------------------------------------

if show_demand:

    fig.add_trace(
        go.Scatter(
            x=total_demand["Datetime"],
            y=total_demand["Value"],
            name="TOTAL DEMAND",
            mode="lines",
            line=dict(
                color="black",
                width=4
            )
        )
    )

# -----------------------------------------------------
# HOVER FORMAT
# -----------------------------------------------------

for trace in fig.data:

    if trace.name != "SHORTAGE":

        trace.hovertemplate = (
            "%{fullData.name}: %{y:.2f} MW"
            "<extra></extra>"
        )

# -----------------------------------------------------
# LAYOUT
# -----------------------------------------------------

fig.update_layout(
    title="Mindoro Dispatch (NET MW)",
    hovermode="x unified",
    height=900,
    xaxis_title="Datetime",
    yaxis_title="MW",
    legend_title="Plant"
)

fig.update_xaxes(
    rangeslider_visible=True
)

# -----------------------------------------------------
# DISPLAY
# -----------------------------------------------------

st.plotly_chart(
    fig,
    use_container_width=True
)

# =====================================================
# DRAG PLANT ORDER (BELOW CHART)
# =====================================================

st.subheader("Drag Plant Order")

plant_order = sort_items(
    items=plant_order,
    direction="vertical"
)
