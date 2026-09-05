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
# LDC SEGMENT SETTINGS
# =====================================================

st.sidebar.subheader("LDC Segmentation")

num_segments = st.sidebar.number_input(
    "Number of Segments",
    min_value=2,
    max_value=8,
    value=4,
    step=1
)

import numpy as np

def optimal_ldc_segments(ldc_values, k):

    y = np.array(ldc_values)

    n = len(y)

    prefix_sum = np.zeros(n + 1)
    prefix_sq = np.zeros(n + 1)

    prefix_sum[1:] = np.cumsum(y)
    prefix_sq[1:] = np.cumsum(y ** 2)

    def segment_sse(i, j):

        count = j - i

        if count <= 0:
            return 0

        seg_sum = (
            prefix_sum[j]
            - prefix_sum[i]
        )

        seg_sq = (
            prefix_sq[j]
            - prefix_sq[i]
        )

        mean = seg_sum / count

        return seg_sq - count * mean * mean

    dp = np.full(
        (k + 1, n + 1),
        np.inf
    )

    split = np.zeros(
        (k + 1, n + 1),
        dtype=int
    )

    dp[0, 0] = 0

    for seg in range(1, k + 1):

        for end in range(1, n + 1):

            for start in range(seg - 1, end):

                cost = (
                    dp[seg - 1, start]
                    + segment_sse(start, end)
                )

                if cost < dp[seg, end]:

                    dp[seg, end] = cost

                    split[seg, end] = start

    boundaries = []

    end = n

    for seg in range(k, 0, -1):

        start = split[seg, end]

        boundaries.append(
            (start, end)
        )

        end = start

    boundaries.reverse()

    return boundaries, dp[k, n]



# =====================================================
# LOAD DURATION CURVE
# =====================================================

st.subheader("Load Duration Curve")

ldc = (
    total_demand["Value"]
    .sort_values(ascending=False)
    .reset_index(drop=True)
)

# Compress LDC for segmentation

max_points = 200

if len(ldc) > max_points:

    step = len(ldc) // max_points

    ldc_seg = (
        ldc.groupby(
            ldc.index // step
        )
        .mean()
        .reset_index(drop=True)
    )

else:

    ldc_seg = ldc.copy()

boundaries, total_sse = (
   optimal_ldc_segments(
    ldc_seg.values,
    num_segments
)
)

sse_results = []

for k in range(1, 9):

    _, sse = optimal_ldc_segments(
        ldc_seg.values,
        k
    )

    sse_results.append({
        "Segments": k,
        "SSE": sse
    })

sse_df = pd.DataFrame(
    sse_results
)

sse_df["Improvement"] = (
    sse_df["SSE"].shift(1)
    - sse_df["SSE"]
)

sse_df["PctImprovement"] = (
    sse_df["Improvement"]
    / sse_df["SSE"].shift(1)
    * 100
)

recommended_segments = 4

for i in range(2, len(sse_df)):

    if (
        sse_df.loc[i, "PctImprovement"]
        < 10
    ):
        recommended_segments = (
            int(
                sse_df.loc[
                    i - 1,
                    "Segments"
                ]
            )
        )
        break

segment_rows = []

scale_factor = len(ldc) / len(ldc_seg)

for i, (start_idx, end_idx) in enumerate(boundaries):

    actual_start = int(
        start_idx * scale_factor
    )

    actual_end = int(
        end_idx * scale_factor
    )

    segment_data = ldc.iloc[
        actual_start:actual_end
    ]

    segment_mean = (
        segment_data.mean()
    )

    segment_sse = (
        (
            segment_data
            - segment_mean
        ) ** 2
    ).sum()

    segment_rows.append({

        "Segment":
            f"S{i+1}",
        "Start %": round(
            actual_start / len(ldc) * 100, 2),

"End %": round(
    actual_end / len(ldc) * 100,
    2
),
        "Avg MW":
            round(segment_mean, 2),

        "Max MW":
            round(
                segment_data.max(),
                2
            ),

        "Min MW":
            round(
                segment_data.min(),
                2
            ),

        "Hours":
            len(segment_data),

        "% Time":
            round(
                len(segment_data)
                /
                len(ldc)
                * 100,
                2
            ),

        "Energy (MWh)":
            round(
                segment_data.sum(),
                2
            ),

        "SSE":
            round(
                segment_sse,
                0
            )
    })
    
segment_table = pd.DataFrame(
    segment_rows
)

ldc_pct = (
    (ldc.index + 1)
    / len(ldc)
    * 100
)

st.caption("Load Segment Summary")

st.metric(
    "Total Segmentation SSE",
    f"{total_sse:,.0f}"
)

fig_elbow = go.Figure()

fig_elbow.add_trace(
    go.Scatter(
        x=sse_df["Segments"],
        y=sse_df["SSE"],
        mode="lines+markers",
        name="SSE"
    )
)

fig_elbow.add_vline(
    x=recommended_segments,
    line_dash="dash",
    annotation_text=
        f"Recommended ({recommended_segments})"
)

fig_elbow.update_layout(
    title="Elbow Method",
    xaxis_title="Number of Segments",
    yaxis_title="SSE",
    height=350
)

st.plotly_chart(
    fig_elbow,
    use_container_width=True
)

st.dataframe(
    segment_table,
    use_container_width=True,
    hide_index=True
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

segment_colors = [
    "red",
    "orange",
    "gold",
    "green",
    "deepskyblue",
    "mediumpurple",
    "gray",
    "brown"
]

scale_factor = len(ldc) / len(ldc_seg)

for i, (start_idx, end_idx) in enumerate(boundaries):

    actual_start = int(
        start_idx * scale_factor
    )

    actual_end = int(
        end_idx * scale_factor
    )

    segment_data = ldc.iloc[
        actual_start:actual_end
    ]

    segment_mean = segment_data.mean()

    start_pct = (
        actual_start
        / len(ldc)
        * 100
    )

    end_pct = (
        actual_end
        / len(ldc)
        * 100
    )

    # Region shading

    fig_ldc.add_vrect(
        x0=start_pct,
        x1=end_pct,
        fillcolor=segment_colors[i],
        opacity=0.08,
        line_width=0,
        annotation_text=f"S{i+1}"
    )

    fig_ldc.add_vline(
        x=end_pct,
        line_dash="dot",
        line_color="black"
    )

    # Piecewise mean line

    fig_ldc.add_trace(
        go.Scatter(
            x=[
                start_pct,
                end_pct
            ],
            y=[
                segment_mean,
                segment_mean
            ],
            mode="lines",
            line=dict(
                color=segment_colors[i],
                width=6
            ),
            name=f"S{i+1} Mean"
        )
    )

fig_ldc.add_hline(
    y=average_load,
    line_dash="dash",
    annotation_text=
        f"Average Load ({average_load:,.2f} MW)"
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

st.subheader("Reserve Margin Analysis")

reserve_curve = (
    gap_df["ReserveMargin"]
    .sort_values(ascending=False)
    .reset_index(drop=True)
)

reserve_pct = (
    (reserve_curve.index + 1)
    / len(reserve_curve)
    * 100
)

fig_reserve = go.Figure()

fig_reserve.add_trace(
    go.Scatter(
        x=reserve_pct,
        y=reserve_curve,
        mode="lines",
        name="Reserve Margin"
    )
)

fig_reserve.add_hline(
    y=5,
    line_dash="dash",
    annotation_text="5 MW Threshold"
)

st.plotly_chart(
    fig_reserve,
    use_container_width=True
)

r1,r2,r3,r4,r5 = st.columns(5)

r1.metric(
    "Minimum Reserve",
    f"{gap_df['ReserveMargin'].min():,.2f}"
)

r2.metric(
    "Median Reserve",
    f"{gap_df['ReserveMargin'].median():,.2f}"
)

r3.metric(
    "P10 Reserve",
    f"{gap_df['ReserveMargin'].quantile(.10):,.2f}"
)

r4.metric(
    "Hours < 5 MW",
    (gap_df["ReserveMargin"] < 5).sum()
)

r5.metric(
    "Hours < 0 MW",
    (gap_df["ReserveMargin"] < 0).sum()
)

st.subheader("Shortage Event Analysis")

gap_df["ShortageFlag"] = gap_df["ShortageMW"] > 0

gap_df["EventID"] = (
    gap_df["ShortageFlag"]
    != gap_df["ShortageFlag"].shift()
).cumsum()

events = []

for event_id, grp in gap_df.groupby("EventID"):

    if not grp["ShortageFlag"].iloc[0]:
        continue

    events.append({
        "Start": grp["Datetime"].min(),
        "End": grp["Datetime"].max(),
        "Duration Hours": (
    grp["Datetime"].max()
    - grp["Datetime"].min()
).total_seconds() / 3600 + 1,
        "Max Shortage MW": round(
            grp["ShortageMW"].max(),
            2
        ),
        "Unserved Energy MWh": round(
            grp["ShortageMW"].sum(),
            2
        )
    })

shortage_events = pd.DataFrame(events)

st.dataframe(
    shortage_events,
    height=350,
    use_container_width=True,
    hide_index=True
)

st.subheader("Plant Contribution Analysis")

plant_summary = (
    generation.groupby("Plant")
    .agg(
        AvgMW=("Value", "mean"),
        PeakMW=("Value", "max"),
        EnergyMWh=("Value", "sum")
    )
    .reset_index()
)

plant_summary["Contribution %"] = (
    plant_summary["EnergyMWh"]
    / plant_summary["EnergyMWh"].sum()
    * 100
)

plant_summary = plant_summary.sort_values(
    "EnergyMWh",
    ascending=False
)

fig_contrib = go.Figure()

fig_contrib.add_trace(
    go.Bar(
        x=plant_summary["Plant"],
        y=plant_summary["EnergyMWh"]
    )
)

fig_contrib.update_layout(
    title="Plant Energy Contribution"
)

st.plotly_chart(
    fig_contrib,
    use_container_width=True
)

st.dataframe(
    plant_summary,
    use_container_width=True,
    hide_index=True
)

st.subheader(
    "Generation Mix at Peak Demand"
)

peak_mix = generation[
    generation["Datetime"] == peak_datetime
].copy()

peak_mix["Percent"] = (
    peak_mix["Value"]
    / peak_mix["Value"].sum()
    * 100
)

peak_mix_display = (
    peak_mix[
        [
            "Plant",
            "Value",
            "Percent"
        ]
    ]
    .sort_values(
        "Value",
        ascending=False
    )
)

st.dataframe(
    peak_mix_display,
    use_container_width=True,
    hide_index=True
)

fig_peak_mix = go.Figure()

fig_peak_mix.add_trace(
    go.Bar(
        x=peak_mix_display["Value"],
        y=peak_mix_display["Plant"],
        orientation="h"
    )
)

fig_peak_mix.update_layout(
    title="Generation Mix at Peak Demand",
    height=500,
    yaxis=dict(
        categoryorder="total ascending"
    )
)

st.plotly_chart(
    fig_peak_mix,
    use_container_width=True
)

growth_rate = st.sidebar.slider(
    "Annual Demand Growth (%)",
    0.0,
    10.0,
    3.0,
    0.1
)

planning_horizon = 10

projected_peak = (
    peak_demand
    * (1 + growth_rate / 100) ** planning_horizon
)

available_capacity = (
    total_generation["TotalGeneration"]
    .max()
)

capacity_margin = (
    available_capacity
    - projected_peak
)

reserve_margin_pct = (
    capacity_margin
    / projected_peak
    * 100
)

required_new_capacity = max(
    projected_peak - available_capacity,
    0
)

st.subheader("Demand Growth & Capacity Outlook")

f1, f2, f3, f4 = st.columns(4)

with f1:
    st.metric(
        "Current Peak Demand",
        f"{peak_demand:,.2f} MW"
    )

with f2:
    st.metric(
        "Projected Peak Demand (10-Year)",
        f"{projected_peak:,.2f} MW"
    )

with f3:
    st.metric(
        "Available Capacity",
        f"{available_capacity:,.2f} MW"
    )

with f4:
    st.metric(
        "Reserve Margin",
        f"{reserve_margin_pct:.1f}%"
    )

st.metric(
    "Required New Capacity",
    f"{required_new_capacity:,.2f} MW"
)

if reserve_margin_pct >= 15:
    st.success("System capacity appears adequate.")
elif reserve_margin_pct >= 0:
    st.warning("System has limited reserve margin.")
else:
    st.error("Projected demand exceeds available capacity.")

projection_rows = []

for yr in range(0, 11):

   projected = (
    peak_demand
    * (1 + growth_rate / 100) ** yr
    )

   reserve = (
        available_capacity
        - projected
    )

    projection_rows.append({
        "Year": yr,
        "Projected Peak MW": round(
            projected,
            2
        ),
        "Capacity Margin MW": round(
            reserve,
            2
        ),
        "Additional Capacity Needed MW": round(
            max(-reserve, 0),
            2
        )
    })

projection_df = pd.DataFrame(
    projection_rows
)

st.caption(
    "10-Year Capacity Planning Outlook"
)

st.dataframe(
    projection_df,
    use_container_width=True,
    hide_index=True
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

with st.expander(
    "Plant Stack Order",
    expanded=False
):

    plant_order = sort_items(
        items=plant_order,
        direction="vertical"
    )
