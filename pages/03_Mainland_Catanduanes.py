import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_sortables import sort_items

# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="Mainland Catanduanes Dispatch Dashboard",
    layout="wide"
)

st.title("Mainland Catanduanes Dispatch Dashboard")

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data
def load_data():

    df = pd.read_excel(
        "Catanduanes Hourly Supply and Demand.xlsm",
        sheet_name="FinalSummary",
        engine="openpyxl"
    )

    df["Datetime"] = pd.to_datetime(
        df["Month"],
        errors="coerce"
    )

    df.rename(
        columns={
            "Power Plant": "Plant"
        },
        inplace=True
    )

    df["Value"] = (
        pd.to_numeric(
            df["Value"],
            errors="coerce"
        ) / 1000
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

df["Month"] = df["Datetime"].dt.month
df["Day"] = df["Datetime"].dt.day

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Filters")

# =====================================================

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
    (df["Month"].isin(selected_months))
    &
    (df["Day"].isin(selected_days))
].copy()

# =====================================================
# TOTAL DEMAND
# =====================================================

total_demand = (
    filtered[
        filtered["Attribute"]
        .astype(str)
        .str.upper()
        .eq("DEMAND (KW)")
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

generation = (
    filtered[
        filtered["Attribute"]
        .astype(str)
        .str.upper()
        .eq("ACTUAL (KW)")
    ]

    .groupby(
        ["Datetime", "Plant"],
        as_index=False
    )["Value"]
    .sum()
)

generation = generation[
    generation["Plant"]
    .astype(str)
    .str.upper()
    != "DEMAND"
]

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

gap_df["ImportSupport"] = 0

gap_df["TotalSupply"] = (
    gap_df["TotalGeneration"]
    +
    gap_df["ImportSupport"]
)

SHORTAGE_THRESHOLD = 0.01

gap_df["ShortageMW"] = (
    gap_df["TotalDemand"]
    - gap_df["TotalSupply"]
).round(2)

gap_df["ShortageArea"] = gap_df["ShortageMW"].clip(lower=0)

gap_df["ReserveMargin"] = (
    gap_df["TotalSupply"]
    - gap_df["TotalDemand"]
)

peak_demand = gap_df["TotalDemand"].max()

peak_row = gap_df.loc[
    gap_df["TotalDemand"].idxmax()
]

peak_datetime = peak_row["Datetime"]

hours_with_shortage = (
    gap_df["ShortageMW"]
    >= SHORTAGE_THRESHOLD
).sum()

max_shortage = max(
    gap_df["ShortageMW"].max(),
    0
)

unserved_energy = (
    gap_df.loc[
        gap_df["ShortageMW"]
        >= SHORTAGE_THRESHOLD,
        "ShortageMW"
    ].sum()
)

hours_low_reserve = (
    gap_df["ReserveMargin"] < 5
).sum()

total_shortage_mwh = gap_df.loc[
    gap_df["ShortageMW"]
    >= SHORTAGE_THRESHOLD,
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

r1c1, r1c2, r1c3, r1c4 = st.columns(4)

with r1c1:
    st.metric(
        "Peak Demand",
        f"{peak_demand:,.2f} MW"
    )

with r1c2:
    st.metric(
        "Maximum Shortage",
        f"{max_shortage:,.2f} MW"
    )

with r1c3:
    st.metric(
        "Unserved Energy",
        f"{unserved_energy:,.2f} MWh"
    )

with r1c4:
    st.metric(
        "Hours with Shortage",
        f"{hours_with_shortage:,}"
    )

r2c1, r2c2 = st.columns(2)

with r2c1:
    st.metric(
        "Low Reserve Hours (<5 MW)",
        f"{hours_low_reserve:,}"
    )

with r2c2:
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
        lambda x: (
        x >= SHORTAGE_THRESHOLD
        ).sum()
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

gap_df["ShortageFlag"] = (
    gap_df["ShortageMW"]
    >= SHORTAGE_THRESHOLD
)

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

generation = generation[
    generation["Plant"].notna()
]

generation = generation[
    generation["Plant"].astype(str).str.strip() != ""
]

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

import plotly.express as px

c1, c2 = st.columns(2)

with c1:

    fig_tree = px.treemap(
        plant_summary,
        path=["Plant"],
        values="EnergyMWh",
        color="Contribution %",
        color_continuous_scale="Blues"
    )

    fig_tree.update_layout(
        title="Generation Share Treemap",
        height=600
    )

    st.plotly_chart(
        fig_tree,
        use_container_width=True
    )

with c2:

    fig_contrib = go.Figure()

    fig_contrib.add_trace(
        go.Bar(
            x=plant_summary["Plant"],
            y=plant_summary["EnergyMWh"],
            text=plant_summary["Contribution %"].round(1),
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )
    )

    fig_contrib.update_layout(
        title="Plant Energy Contribution",
        xaxis_title="Plant",
        yaxis_title="Energy (MWh)",
        xaxis_tickangle=-45,
        height=600
    )

    st.plotly_chart(
        fig_contrib,
        use_container_width=True
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

st.subheader(
    f"Demand Growth & Capacity Outlook (@ {growth_rate:.1f}% Annual Growth)"
)

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
        "Year Ahead": yr,
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
    f"10-Year Capacity Planning Outlook @ {growth_rate:.1f}% Annual Demand Growth"
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
    - gap_df["TotalSupply"]
).clip(lower=0)

# -----------------------------------------------------
# ORANGE SHORTAGE SHADE
# -----------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=gap_df["Datetime"],
        y=gap_df["TotalSupply"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
        hovertemplate=None,
        name=""
    )
)

fig.add_trace(
    go.Scatter(
        x=gap_df["Datetime"],
        y=gap_df["TotalSupply"]
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

gap_df["TotalSupply"] = (
    gap_df["TotalGeneration"]
    +
    gap_df["ImportSupport"]
)

fig.add_trace(
    go.Scatter(
        x=gap_df["Datetime"],
        y=gap_df["TotalSupply"],
        name="TOTAL SUPPLY",
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

    if (
        trace.name is not None
        and trace.name != ""
        and trace.name != "SHORTAGE"
    ):

        trace.hovertemplate = (
            "%{fullData.name}: %{y:.2f} MW"
            "<extra></extra>"
        )

# -----------------------------------------------------
# LAYOUT
# -----------------------------------------------------

fig.update_layout(
    title="Catanduanes Dispatch",
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

# =====================================================
# PEAK HOUR PERFORMANCE ANALYSIS
# =====================================================

st.subheader(
    "Peak Hour Performance Analysis (90%-100% of Peak Demand)"
)

peak_threshold = peak_demand * 0.90

peak_hours = total_demand.loc[
    total_demand["Value"] >= peak_threshold,
    "Datetime"
]

peak_generation = generation[
    generation["Datetime"].isin(peak_hours)
].copy()

# -----------------------------------------------------
# PEAK HOUR SNAPSHOT
# -----------------------------------------------------

peak_snapshot = (
    peak_generation
    .groupby("Plant")
    .agg(
        AvgPeakMW=("Value", "mean"),
        MaxPeakMW=("Value", "max"),
        PeakEnergyMWh=("Value", "sum")
    )
    .reset_index()
)

peak_snapshot["PeakEnergyShare %"] = (
    peak_snapshot["PeakEnergyMWh"]
    /
    peak_snapshot["PeakEnergyMWh"].sum()
    * 100
)

peak_snapshot = peak_snapshot.sort_values(
    "PeakEnergyShare %",
    ascending=False
)

st.markdown(
    """
    **Story:** During hours when system demand reached at least
    90% of peak demand, the following plants supported the grid.
    """
)

st.dataframe(
    peak_snapshot,
    use_container_width=True,
    hide_index=True
)

fig_peak_support = go.Figure()

fig_peak_support.add_trace(
    go.Bar(
        y=peak_snapshot["Plant"],
        x=peak_snapshot["PeakEnergyShare %"],
        orientation="h",
        text=peak_snapshot["PeakEnergyShare %"].round(1),
        texttemplate="%{text:.1f}%",
        textposition="outside"
    )
)

fig_peak_support.update_layout(
    title="Peak Hour Energy Contribution Share",
    xaxis_title="Peak Energy Share (%)",
    yaxis_title="Plant",
    height=550,
    yaxis=dict(
        categoryorder="total ascending"
    )
)

st.plotly_chart(
    fig_peak_support,
    use_container_width=True
)

# =====================================================
# PEAK HOUR GENERATION MIX
# =====================================================

st.subheader(
    "Peak Hour Generation Mix"
)

daily_peak_hour = (
    total_demand
    .assign(Date=total_demand["Datetime"].dt.date)
    .sort_values(
        ["Date", "Value"],
        ascending=[True, False]
    )
    .groupby("Date", as_index=False)
    .first()
)

daily_peak_gen = generation.merge(
    daily_peak_hour[["Datetime"]],
    on="Datetime",
    how="inner"
)

daily_peak_total = (
    daily_peak_gen
    .groupby("Datetime")["Value"]
    .sum()
    .rename("Total")
)

daily_peak_gen = daily_peak_gen.merge(
    daily_peak_total,
    on="Datetime",
    how="left"
)

daily_peak_gen["Share"] = (
    daily_peak_gen["Value"]
    /
    daily_peak_gen["Total"]
    * 100
)

fig_mix = go.Figure()

for plant in peak_snapshot["Plant"]:

    temp = daily_peak_gen[
        daily_peak_gen["Plant"] == plant
    ]

    fig_mix.add_trace(
        go.Bar(
            x=temp["Datetime"].dt.date,
            y=temp["Share"],
            name=plant
        )
    )

fig_mix.update_layout(
    barmode="stack",
    title="Generation Mix During Daily System Peaks",
    xaxis_title="Date",
    yaxis_title="Share (%)",
    height=650
)

st.plotly_chart(
    fig_mix,
    use_container_width=True
)

# -----------------------------------------------------
# CAPACITY DATA
# -----------------------------------------------------

capacity_data = df[
    df["Attribute"]
    .astype(str)
    .str.upper()
    .isin(
        [
            "INSTALLED CAPACITY (KW)",
            "DEPENDABLE CAPACITY (KW)",
            "AVAILABLE CAPACITY (KW)"
        ]
    )
].copy()

capacity_data["Attribute"] = (
    capacity_data["Attribute"]
    .astype(str)
    .str.upper()
)

available_capacity_tbl = (
    capacity_data[
        capacity_data["Attribute"]
        == "AVAILABLE CAPACITY (KW)"
    ]
    .groupby("Plant")
    .agg(
        AvailableMW=("Value", "sum")
    )
    .reset_index()
)

# -----------------------------------------------------
# PERFORMANCE TABLE
# -----------------------------------------------------

performance = peak_snapshot.merge(
    available_capacity_tbl,
    on="Plant",
    how="left"
)

performance["Peak Support %"] = (
    performance["MaxPeakMW"]
    /
    performance["AvailableMW"]
    * 100
)

performance.loc[
    performance["AvailableMW"] <= 0,
    "Peak Support %"
] = None

# -----------------------------------------------------
# RISK FLAG
# -----------------------------------------------------

def get_flag(row):

    avail = row["AvailableMW"]
    ach = row["Peak Support %"]

    if pd.isna(avail):
        return "No Data"

    if avail <= 0:
        return "Outage"

    if ach >= 90:
        return "OK"

    if ach >= 70:
        return "Monitor"

    return "Investigate"

performance["Risk Flag"] = (
    performance.apply(
        get_flag,
        axis=1
    )
)

# -----------------------------------------------------
# REMARKS
# -----------------------------------------------------

def get_remarks(row):

    plant = str(row["Plant"]).upper()

    if row["Risk Flag"] == "Outage":
        return "Unit unavailable during analysis period."

    if row["Risk Flag"] == "OK":
        return (
            "Plant achieved available capability "
            "during peak hours."
        )

    if row["Risk Flag"] == "Monitor":

        if "MHP" in plant:
            return (
                "Moderate hydro utilization. "
                "Review water availability."
            )

        return (
            "Below full capability during peak conditions."
        )

    if row["Risk Flag"] == "Investigate":

        if "MHP" in plant:
            return (
                "Low hydro output versus available "
                "capacity. Check water resource or "
                "operational constraints."
            )

        return (
            "Available but did not achieve expected "
            "capability during peak demand. Review "
            "derating, maintenance, fuel supply, "
            "or dispatch strategy."
        )

    return ""

performance["Remarks"] = (
    performance.apply(
        get_remarks,
        axis=1
    )
)

performance = performance.sort_values(
    "Peak Support %",
    ascending=True
)

st.markdown(
    """
    **Story:** Evaluates whether each plant achieved its
    available capability during critical demand periods.
    """
)

st.dataframe(
    performance[
        [
            "Plant",
            "AvailableMW",
            "AvgPeakMW",
            "MaxPeakMW",
            "Peak Support %",
            "Risk Flag",
            "Remarks"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# -----------------------------------------------------
# ACHIEVEMENT CHART
# -----------------------------------------------------

color_map = {
    "OK": "green",
    "Monitor": "gold",
    "Investigate": "red",
    "Outage": "gray",
    "No Data": "lightgray"
}

fig_perf = go.Figure()

for flag in performance["Risk Flag"].unique():

    temp = performance[
        performance["Risk Flag"] == flag
    ]

    fig_perf.add_trace(
        go.Bar(
            y=temp["Plant"],
            x=temp["Peak Support %"],
            orientation="h",
            name=flag,
            marker_color=color_map.get(
                flag,
                "blue"
            )
        )
    )

fig_perf.update_layout(
    title=(
    "Peak Support During Critical Hours "
    "(Max Peak MW / Available MW)"
),
    xaxis_title="Peak Support (%)",
    yaxis_title="Plant",
    height=600,
    barmode="group"
)

fig_perf.add_vline(
    x=90,
    line_dash="dash",
    line_color="green"
)

fig_perf.add_vline(
    x=70,
    line_dash="dash",
    line_color="orange"
)

st.plotly_chart(
    fig_perf,
    use_container_width=True
)

# =====================================================
# SECTION 3
# ASSET PERFORMANCE ASSESSMENT
# =====================================================

st.subheader(
    "Plant Asset Performance Assessment"
)

st.markdown(
    """
    **Story:** Evaluates whether each plant was capable of
    realizing its available capability at any point during
    the study period, independent of system peak demand.
    """
)

# -----------------------------------------------------
# AVAILABLE CAPACITY
# -----------------------------------------------------

dependable_capacity_tbl = (
    capacity_data[
        capacity_data["Attribute"]
        == "DEPENDABLE CAPACITY (KW)"
    ]
    .groupby("Plant", as_index=False)
    .agg(
        DependableMW=("Value", "sum")
    )
)

# -----------------------------------------------------
# OVERALL PERFORMANCE
# -----------------------------------------------------

asset_perf = (
    generation
    .groupby("Plant", as_index=False)
    .agg(
        AvgMW=("Value", "mean"),
        MaxObservedMW=("Value", "max"),
        EnergyMWh=("Value", "sum")
    )
)

asset_perf = asset_perf.merge(
    dependable_capacity_tbl,
    on="Plant",
    how="left"
)

# -----------------------------------------------------
# UTILIZATION FACTOR
# -----------------------------------------------------

asset_perf["UtilizationFactor %"] = (
    asset_perf["AvgMW"]
    /
    asset_perf["DependableMW"]
    * 100
)

# -----------------------------------------------------
# CAPABILITY REALIZATION
# -----------------------------------------------------

asset_perf["CapabilityRealization %"] = (
    asset_perf["MaxObservedMW"]
    /
    asset_perf["DependableMW"]
    *100
)

asset_perf.loc[
    asset_perf["DependableMW"] <= 0,
    "CapabilityRealization %"
] = None

# -----------------------------------------------------
# RISK FLAG
# -----------------------------------------------------

def asset_flag(row):

    avail = row["DependableMW"]
    realization = row["CapabilityRealization %"]

    if pd.isna(avail):
        return "No Data"

    if avail <= 0:
        return "Outage"

    if realization >= 95:
        return "OK"

    if realization >= 75:
        return "Monitor"

    return "Investigate"

asset_perf["Risk Flag"] = (
    asset_perf.apply(
        asset_flag,
        axis=1
    )
)

# -----------------------------------------------------
# REMARKS
# -----------------------------------------------------

def asset_remark(row):

    plant = str(row["Plant"]).upper()

    if row["Risk Flag"] == "Outage":
        return (
            "No available capacity recorded."
        )

    if row["Risk Flag"] == "OK":
        return (
            "Plant achieved available capability "
            "during study period."
        )

    if row["Risk Flag"] == "Monitor":
        return (
            "Plant approached available capability "
            "but did not fully realize it."
        )

    if "MHP" in plant:
        return (
            "Plant never achieved available capability. "
            "Investigate water resource, equipment "
            "condition, or operational constraints."
        )

    return (
        "Plant never achieved available capability. "
        "Review derating, maintenance history, fuel "
        "availability, and dispatch restrictions."
    )

asset_perf["Remarks"] = (
    asset_perf.apply(
        asset_remark,
        axis=1
    )
)

asset_perf = asset_perf.sort_values(
    "CapabilityRealization %",
    ascending=True
)

# -----------------------------------------------------
# TABLE
# -----------------------------------------------------

st.dataframe(
    asset_perf[
        [
            "Plant",
            "DependableMW",
            "AvgMW",
            "MaxObservedMW",
            "UtilizationFactor %",
            "CapabilityRealization %",
            "Risk Flag",
            "Remarks"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# -----------------------------------------------------
# CHART
# -----------------------------------------------------

asset_color_map = {
    "OK": "green",
    "Monitor": "gold",
    "Investigate": "red",
    "Outage": "gray",
    "No Data": "lightgray"
}

fig_asset = go.Figure()

for flag in asset_perf["Risk Flag"].unique():

    temp = asset_perf[
        asset_perf["Risk Flag"] == flag
    ]

    fig_asset.add_trace(
        go.Bar(
            y=temp["Plant"],
            x=temp["CapabilityRealization %"],
            orientation="h",
            name=flag,
            marker_color=asset_color_map.get(
                flag,
                "blue"
            )
        )
    )

fig_asset.add_vline(
    x=95,
    line_dash="dash",
    line_color="green"
)

fig_asset.add_vline(
    x=75,
    line_dash="dash",
    line_color="orange"
)

fig_asset.update_layout(
    title="Capability Realization by Plant",
    xaxis_title="Max Observed MW / Dependable MW (%)",
    yaxis_title="Plant",
    height=650,
    barmode="group"
)

st.plotly_chart(
    fig_asset,
    use_container_width=True
)

# =====================================================
# UNIT CAPABILITY REALIZATION
# =====================================================

st.subheader(
    "Unit Capability Realization"
)

if "Unit/Contract" in df.columns:

    unit_generation = (
        filtered[
            filtered["Attribute"]
            .astype(str)
            .str.upper()
            .eq("ACTUAL (KW)")
        ]
        .groupby(
            ["Plant", "Unit/Contract"],
            as_index=False
        )
        .agg(
            MaxObservedMW=("Value", "max")
        )
    )

    if "Unit/Contract" in df.columns:

    ...
    
else:

    st.warning(
        "Column 'Unit/Contract' not found."
    )

    st.stop()

    unit_dependable = (
        capacity_data[
            capacity_data["Attribute"]
            == "DEPENDABLE CAPACITY (KW)"
        ]
        .groupby(
            ["Plant", "Unit/Contract"],
            as_index=False
        )
        .agg(
            DependableMW=("Value", "max")
        )
    )

    unit_perf = unit_generation.merge(
        unit_dependable,
        on=["Plant", "Unit/Contract"],
        how="left"
    )

    unit_perf["CapabilityRealization %"] = (
        unit_perf["MaxObservedMW"]
        /
        unit_perf["DependableMW"]
        * 100
    )

unit_perf = unit_perf.sort_values(
    ["Plant", "CapabilityRealization %"],
    ascending=[True, True]
)

unit_perf["PlantUnit"] = (
    unit_perf["Plant"]
    + " | "
    + unit_perf["Unit/Contract"].astype(str)
)

fig_unit = go.Figure()

fig_unit.add_trace(
    go.Bar(
        y=unit_perf["PlantUnit"],
        x=unit_perf["CapabilityRealization %"],
        orientation="h"
    )
)

fig_unit.add_vline(
    x=95,
    line_dash="dash",
    line_color="green"
)

fig_unit.add_vline(
    x=75,
    line_dash="dash",
    line_color="orange"
)

fig_unit.update_layout(
    title="Unit Capability Realization",
    xaxis_title="Max Output / Dependable Capacity (%)",
    yaxis_title="Plant | Unit",
    height=max(700, len(unit_perf) * 25)
)

st.plotly_chart(
    fig_unit,
    use_container_width=True
)

st.write(df.columns.tolist())

st.write(
    sorted(capacity_data["Attribute"].unique())
)

