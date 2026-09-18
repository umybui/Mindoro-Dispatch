import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_sortables import sort_items

# =====================================================
# PAGE
# =====================================================

st.set_page_config(
    page_title="Mainland Palawan Dispatch Dashboard",
    layout="wide"
)

st.title("Mainland Palawan Dispatch Dashboard")
#try
# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data
def load_data():

    df = pd.read_excel(
        "PALECO Dispatch Summary.xlsx",
        sheet_name="2  PALECO Reports",
        engine="openpyxl"
    )

    df["Datetime"] = pd.to_datetime(
        df["Datetime"],
        errors="coerce"
    )

    df["NumericValue"] = pd.to_numeric(
        df["NumericValue"],
        errors="coerce"
    )

    df["Value"] = df["NumericValue"]

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
        (
            filtered["Plant"]
            .astype(str)
            .str.upper()
            == "DEMAND"
        )
        &
        (
            filtered["Attribute"]
            .astype(str)
            .str.upper()
            == "TOTAL GRID DEMAND"
        )
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
        .eq("OUTPUT")
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

# Reserve Requirement Components

gap_df["RegulatingReserve"] = (
    gap_df["TotalDemand"] * 0.028
)

gap_df["ContingencyReserve"] = (
    gap_df["TotalGeneration"] * 0.10
)

gap_df["RequiredReserve"] = (
    gap_df["RegulatingReserve"]
    +
    gap_df["ContingencyReserve"]
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
    gap_df["ReserveMargin"]
    < gap_df["RequiredReserve"]
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

peak_generation_mw = (
    gap_df["TotalGeneration"]
    .max()
)

demand_energy_mwh = (
    total_demand["Value"]
    .sum()
)

generated_energy_mwh = (
    total_generation["TotalGeneration"]
    .sum()
)

energy_served_pct = (
    (
        demand_energy_mwh
        - unserved_energy
    )
    /
    demand_energy_mwh
    * 100
    if demand_energy_mwh > 0
    else 0
)

average_load = total_demand["Value"].mean()

load_factor = (
    average_load
    / peak_demand
    * 100
)

# =====================================================
# KPI DISPLAY
# =====================================================

r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)

with r1c1:
    st.metric(
        "Peak Demand",
        f"{peak_demand:,.2f} MW"
    )

with r1c2:
    st.metric(
        "Demand Energy",
        f"{demand_energy_mwh:,.2f} MWh"
    )

with r1c3:
    st.metric(
        "Generated Energy",
        f"{generated_energy_mwh:,.2f} MWh"
    )

with r1c4:
    st.metric(
        "Unserved Energy",
        f"{unserved_energy:,.2f} MWh"
    )

with r1c5:
    st.metric(
        "Energy Served",
        f"{energy_served_pct:.2f}%"
    )

r2c1, r2c2, r2c3, r2c4 = st.columns(4)

with r2c1:
    st.metric(
        "Hours with Shortage",
        f"{hours_with_shortage:,}"
    )

with r2c2:
    st.metric(
        "Low Reserve Hours",
        f"{hours_low_reserve:,}"
    )

with r2c3:
    st.metric(
        "Load Factor",
        f"{load_factor:.1f}%"
    )

with r2c4:
    st.metric(
        "Peak Demand Time",
        peak_datetime.strftime(
            "%Y-%m-%d %H:%M"
        )
    )

# =====================================================
# GENERATION MIX BY TECHNOLOGY
# =====================================================

def get_technology(plant):

    plant = str(plant).upper()

    # Bunker
    if (
        "E-DELTA" in plant
        or "EDELTA" in plant
        or "ABORLAN" in plant
    ):
        return "Bunker"

    # Thermal
    if "NARRA" in plant:
        return "Thermal"

    # Diesel
    if any(
        x in plant
        for x in [
            "T-DELTA",
            "TDELTA",
            "QUEZON",
            "IRAWAN",
            "EPSA",
            "RIO TUBA",
            "VPOWER"
        ]
    ):
        return "Diesel"

    return "Other"

generation["Technology"] = (
    generation["Plant"]
    .apply(get_technology)
)

# -----------------------------------------------------
# OVERALL TECHNOLOGY MIX
# -----------------------------------------------------

tech_mix = (
    generation
    .groupby(
        "Technology",
        as_index=False
    )["Value"]
    .sum()
)

tech_mix["Share"] = (
    tech_mix["Value"]
    /
    tech_mix["Value"].sum()
    * 100
)

tech_mix = tech_mix.sort_values(
    "Share",
    ascending=False
)

tech_colors = {
    "Diesel": "#1565C0",
    "Thermal": "#E53935",
    "Bunker": "#FB8C00",
    "Other": "#757575"
}

fig_tech = go.Figure()

for _, row in tech_mix.iterrows():

    fig_tech.add_trace(
        go.Bar(
            y=[""],
            x=[row["Share"]],
            name=row["Technology"],
            orientation="h",
            marker_color=tech_colors.get(
                row["Technology"],
                "#757575"
            ),
            text=(
                f"{row['Technology']}<br>"
                f"{row['Share']:.1f}%"
            ),
            textposition="inside",
            textfont=dict(
                color="white",
                size=12
            )
        )
    )

fig_tech.update_layout(
    barmode="stack",
    height=220,
    margin=dict(
        l=20,
        r=20,
        t=20,
        b=20
    ),
    xaxis_title="Share of Generated Energy (%)",
    yaxis_title="",
    showlegend=False
)

show_breakdown = st.toggle(
    "Break down by power plant",
    value=False
)

# =====================================================
# CONSTANT CHART HEIGHT
# =====================================================

MIX_HEIGHT = 220

# =====================================================
# TECHNOLOGY VIEW
# =====================================================

fig_tech.update_layout(
    barmode="stack",
    height=MIX_HEIGHT,
    margin=dict(
        l=20,
        r=20,
        t=20,
        b=40
    ),
    xaxis_title="Share of Generated Energy (%)",
    yaxis_title="",
    showlegend=False
)

if not show_breakdown:

    st.plotly_chart(
        fig_tech,
        use_container_width=True
    )

# =====================================================
# POWER PLANT BREAKDOWN
# =====================================================

else:

    plant_mix = (
        generation
        .groupby(
            ["Technology", "Plant"],
            as_index=False
        )["Value"]
        .sum()
    )

    plant_mix["Share"] = (
        plant_mix["Value"]
        /
        plant_mix["Value"].sum()
        * 100
    )

    tech_order = [
        "Bunker",
        "Thermal",
        "Diesel",
        "Other"
    ]

    fig_plant_mix = go.Figure()

    color_map = {
        "Bunker": [
            "#E65100",
            "#F57C00",
            "#FFB74D",
            "#FFE0B2"
        ],
        "Thermal": [
            "#B71C1C",
            "#D32F2F",
            "#EF5350",
            "#FFCDD2"
        ],
        "Diesel": [
            "#0D47A1",
            "#1565C0",
            "#1976D2",
            "#42A5F5",
            "#90CAF9",
            "#BBDEFB",
            "#E3F2FD"
        ],
        "Other": [
            "#757575"
        ]
    }

    running_position = 0

    for tech in tech_order:

        tech_data = plant_mix[
            plant_mix["Technology"] == tech
        ].copy()

        if tech_data.empty:
            continue

        tech_data = tech_data.sort_values(
            "Share",
            ascending=False
        )

        tech_total = tech_data["Share"].sum()

        midpoint = running_position + tech_total / 2

        fig_plant_mix.add_annotation(
            x=midpoint,
            y=1.25,
            xref="x",
            yref="paper",
            text=f"<b>{tech.upper()}</b>",
            showarrow=False,
            font=dict(
                size=14
            )
        )

        shades = color_map.get(
            tech,
            ["#757575"]
        )

        for i, (_, row) in enumerate(
            tech_data.iterrows()
        ):

            color = shades[
                min(
                    i,
                    len(shades) - 1
                )
            ]

            fig_plant_mix.add_trace(
                go.Bar(
                    y=[""],
                    x=[row["Share"]],
                    name=row["Plant"],
                    orientation="h",
                    marker=dict(
                        color=color,
                        line=dict(
                            color="white",
                            width=2
                        )
                    ),
                    text=(
                        f"{row['Plant']}<br>"
                        f"{row['Share']:.1f}%"
                    ),
                    textposition="inside"
                )
            )

        running_position += tech_total

        if running_position < 100:

            fig_plant_mix.add_vline(
                x=running_position,
                line_width=4,
                line_color="white"
            )

    fig_plant_mix.update_layout(
    barmode="stack",
    height=MIX_HEIGHT,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=80
    ),
    xaxis_title="Share of Generated Energy (%)",
    yaxis_title="",

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.30,
        xanchor="center",
        x=0.5
    ),

    showlegend=False
)

    st.plotly_chart(
        fig_plant_mix,
        use_container_width=True
    )

# -----------------------------------------------------
# MONTHLY TECHNOLOGY SHARE HEATMAP
# -----------------------------------------------------

generation["MonthLabel"] = (
    generation["Datetime"]
    .dt.strftime("%b %Y")
)

tech_month = (
    generation
    .groupby(
        ["MonthLabel", "Technology"],
        as_index=False
    )["Value"]
    .sum()
)

month_total = (
    tech_month
    .groupby("MonthLabel")["Value"]
    .sum()
)

tech_month["Share"] = (
    tech_month["Value"]
    /
    tech_month["MonthLabel"]
    .map(month_total)
    * 100
)

heat_tech = (
    tech_month
    .pivot(
        index="Technology",
        columns="MonthLabel",
        values="Share"
    )
    .fillna(0)
)

tech_order = [
    "Diesel",
    "Thermal",
    "Bunker",
    "Other"
]

heat_tech = (
    heat_tech
    .reindex(tech_order)
    .fillna(0)
)

month_order = (
    generation
    .assign(
        MonthDate=
        generation["Datetime"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )
    [["MonthLabel", "MonthDate"]]
    .drop_duplicates()
    .sort_values("MonthDate")
)

valid_months = [
    m
    for m in month_order["MonthLabel"]
    if m in heat_tech.columns
]

heat_tech = heat_tech[
    valid_months
]

fig_tech_heat = go.Figure(
    data=go.Heatmap(
        z=heat_tech.values,
        x=heat_tech.columns,
        y=heat_tech.index,
        colorscale="Blues",
        text=heat_tech.round(1).values,
        texttemplate="%{text}%",
        colorbar_title="% Share"
    )
)

fig_tech_heat.update_layout(
    title="Monthly Generation Share by Technology",
    height=300
)

st.plotly_chart(
    fig_tech_heat,
    use_container_width=True
)

with st.expander(
    "View Monthly Technology Share Matrix (%)",
    expanded=False
):

    st.dataframe(
        heat_tech.round(1)
        .style.format("{:.1f}%"),
        use_container_width=True
    )

# =====================================================
# MONTHLY RELIABILITY OVERVIEW
# =====================================================

gap_df["MonthYear"] = (
    gap_df["Datetime"]
    .dt.to_period("M")
    .astype(str)
)

gap_df["LowReserveFlag"] = (
            gap_df["ReserveMargin"]
            < gap_df["RequiredReserve"]
        )

monthly_summary = (
    gap_df
    .groupby("MonthYear")
    .agg(
        PeakDemand=("TotalDemand", "max"),

        AverageDemand=(
            "TotalDemand",
            "mean"
        ),

        MinimumReserve=(
            "ReserveMargin",
            "min"
        ),

        MaxShortage=(
            "ShortageMW",
            "max"
        ),

        HoursWithShortage=(
            "ShortageMW",
            lambda x: (
                x >= SHORTAGE_THRESHOLD
            ).sum()
        ),

        CriticalHours=(
            "ReserveMargin",
            lambda x: (
                x < 0
            ).sum()
        ),
      
        LowReserveHours=(
            "LowReserveFlag",
            "sum"
        ),

        UnservedEnergy=(
            "ShortageMW",
            lambda x: (
                x.clip(lower=0)
            ).sum()
        )
    )
    .reset_index()
)

monthly_summary["MonthDate"] = pd.to_datetime(
    monthly_summary["MonthYear"]
)

monthly_summary["MonthName"] = (
    monthly_summary["MonthDate"]
    .dt.strftime("%b %Y")
)

monthly_summary["LoadFactor"] = (
    monthly_summary["AverageDemand"]
    /
    monthly_summary["PeakDemand"]
    * 100
)

hours_per_month = (
    gap_df
    .groupby("MonthYear")
    .size()
    .reset_index(name="TotalHours")
)

monthly_summary = monthly_summary.merge(
    hours_per_month,
    on="MonthYear",
    how="left"
)

monthly_summary["ReserveAdequacyPct"] = (
    (
        monthly_summary["TotalHours"]
        -
        monthly_summary["LowReserveHours"]
    )
    /
    monthly_summary["TotalHours"]
    * 100
)

monthly_summary["EnergyNotServedPct"] = (
    monthly_summary["UnservedEnergy"]
    /
    (
        monthly_summary["AverageDemand"]
        *
        monthly_summary["TotalHours"]
    )
    * 100
)

monthly_summary = (
    monthly_summary
    .sort_values("MonthDate")
)

# =====================================================
# RELIABILITY HEALTH MONITOR
# =====================================================

st.subheader(
    "Reliability Health Monitor"
)

# -----------------------------------------------------
# SCORING WEIGHTS
# -----------------------------------------------------

st.markdown(
    """
    The three weights must total exactly 100%.
    """
)

w1, w2, w3 = st.columns(3)

with w1:
    w_unserved = st.number_input(
        "Unserved Energy Weight (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=1
    )

with w2:
    w_shortage = st.number_input(
        "Shortage Hours Weight (%)",
        min_value=0,
        max_value=100,
        value=25,
        step=1
    )

with w3:
    w_reserve = st.number_input(
        "Low Reserve Hours Weight (%)",
        min_value=0,
        max_value=100,
        value=25,
        step=1
    )

total_weight = (
    w_unserved
    + w_shortage
    + w_reserve
)

if total_weight == 100:

    st.success(
        "✓ Weight Total = 100%"
    )

else:

    st.error(
        f"""
        Weight Total = {total_weight}%

        Reliability score weights must total exactly 100%.
        Please adjust the weights before continuing.
        """
    )

    st.stop()


# -----------------------------------------------------
# COMPONENT SCORES
# -----------------------------------------------------

max_ens_pct = max(
    monthly_summary["EnergyNotServedPct"].max(),
    0.0001
)

max_shortage_hours = max(
    monthly_summary["HoursWithShortage"].max(),
    1
)

monthly_summary["ENS_Score"] = (
    100
    -
    (
        monthly_summary["EnergyNotServedPct"]
        / max_ens_pct
        * 100
    )
)

monthly_summary["Shortage_Score"] = (
    100
    -
    (
        monthly_summary["HoursWithShortage"]
        / max_shortage_hours
        * 100
    )
)

monthly_summary["Reserve_Score"] = (
    monthly_summary["ReserveAdequacyPct"]
)

# -----------------------------------------------------
# RELIABILITY SCORE COMPONENTS
# -----------------------------------------------------

def score_unserved_energy_pct(x):

    if x <= 0.10:
        return 100

    elif x <= 0.50:
        return 80

    elif x <= 1.00:
        return 60

    elif x <= 2.00:
        return 40

    return 20


def score_shortage_hours(x):

    if x == 0:
        return 100

    elif x <= 24:
        return 80

    elif x <= 100:
        return 60

    elif x <= 300:
        return 40

    return 20


def score_reserve_adequacy(x):

    if x >= 95:
        return 100

    elif x >= 90:
        return 80

    elif x >= 80:
        return 60

    elif x >= 70:
        return 40

    return 20


monthly_summary["ENS_Score"] = (
    monthly_summary["EnergyNotServedPct"]
    .apply(score_unserved_energy_pct)
)

monthly_summary["Shortage_Score"] = (
    monthly_summary["HoursWithShortage"]
    .apply(score_shortage_hours)
)

monthly_summary["Reserve_Score"] = (
    monthly_summary["ReserveAdequacyPct"]
    .apply(score_reserve_adequacy)
)

# -----------------------------------------------------
# RELIABILITY SCORE
# -----------------------------------------------------

monthly_summary["ReliabilityScore"] = (
    (
        monthly_summary["ENS_Score"]
        * w_unserved
    )
    +
    (
        monthly_summary["Shortage_Score"]
        * w_shortage
    )
    +
    (
        monthly_summary["Reserve_Score"]
        * w_reserve
    )
) / 100

# -----------------------------------------------------
# TRAFFIC LIGHT STATUS
# -----------------------------------------------------

def get_status(score):

    if score >= 85:
        return "🟢 Excellent"

    elif score >= 70:
        return "🟡 Good"

    elif score >= 50:
        return "🟠 Fair"

    return "🔴 Poor"


monthly_summary["Status"] = (
    monthly_summary["ReliabilityScore"]
    .apply(get_status)
)

# -----------------------------------------------------
# RELIABILITY STATUS CARD
# -----------------------------------------------------

latest = monthly_summary.iloc[-1]

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
    "Reliability Score",
    f"{latest['ReliabilityScore']:.0f}"
    )

    st.caption(
        latest["Status"]
    )

with c2:

    st.metric(
        "Unserved Energy",
        f"{latest['UnservedEnergy']:,.1f} MWh"
    )

# Reserve Adequacy Rating
if latest["ReserveAdequacyPct"] >= 95:
    reserve_status = "🟢 Excellent"

elif latest["ReserveAdequacyPct"] >= 90:
    reserve_status = "🟡 Good"

elif latest["ReserveAdequacyPct"] >= 80:
    reserve_status = "🟠 Fair"

else:
    reserve_status = "🔴 Poor"

with c3:

    st.metric(
        "Reserve Adequacy",
        f"{latest['ReserveAdequacyPct']:.1f}%"
    )

    st.caption(
        reserve_status
    )

with c4:

    st.metric(
        "Low Reserve Hours",
        f"{latest['LowReserveHours']:,.0f}"
    )

# -----------------------------------------------------
# MONTHLY TRAFFIC LIGHT TIMELINE
# -----------------------------------------------------

timeline = "   ".join(

    [
        f"{m[:3]} {s.split()[0]}"
        for m, s
        in zip(
            monthly_summary["MonthName"],
            monthly_summary["Status"]
        )
    ]

)

st.markdown(
    f"### {timeline}"
)

st.caption(
    """
    Traffic Light Legend:

    🟢 Excellent (Score ≥ 85) |
    🟡 Good (70-84) |
    🟠 Fair (50-69) |
    🔴 Poor (<50)
    """
)

# -----------------------------------------------------
# MONTHLY UNSERVED ENERGY TREND
# -----------------------------------------------------

def get_bar_color(x):

    if x <= 0.10:
        return "#2E7D32"

    elif x <= 0.50:
        return "#FDD835"

    elif x <= 2.00:
        return "#FB8C00"

    return "#C62828"


monthly_summary["BarColor"] = (
    monthly_summary["EnergyNotServedPct"]
    .apply(get_bar_color)
)

fig_ue = go.Figure()

fig_ue.add_trace(

    go.Bar(
        x=monthly_summary["MonthName"],
        y=monthly_summary["UnservedEnergy"],
        text=monthly_summary["UnservedEnergy"].round(1),
        textposition="outside",
        marker_color=monthly_summary["BarColor"],
        customdata=monthly_summary[
            "EnergyNotServedPct"
        ],
        hovertemplate=
            "<b>%{x}</b><br>"
            "Unserved Energy: %{y:.2f} MWh<br>"
            "Energy Not Served: %{customdata:.3f}%"
            "<extra></extra>"
    )

)

fig_ue.update_layout(
    title="Monthly Unserved Energy Trend",
    xaxis_title="Month",
    yaxis_title="Unserved Energy (MWh)",
    height=450
)

st.plotly_chart(
    fig_ue,
    use_container_width=True
)

# -----------------------------------------------------
# RESERVE ADEQUACY TREND
# -----------------------------------------------------

fig_reserve_health = go.Figure()

fig_reserve_health.add_trace(
    go.Scatter(
        x=monthly_summary["MonthName"],
        y=monthly_summary["ReserveAdequacyPct"],
        mode="lines+markers+text",
        text=(
            monthly_summary["ReserveAdequacyPct"]
            .round(1)
            .astype(str)
            + "%"
        ),
        textposition="top center",
        line=dict(
            width=3,
            color="#1f77b4"
        ),
        marker=dict(
            size=8
        ),
        hovertemplate=
            "<b>%{x}</b><br>"
            "Reserve Adequacy: %{y:.1f}%"
            "<extra></extra>"
    )
)

# Excellent threshold
fig_reserve_health.add_hline(
    y=95,
    line_dash="dash",
    line_color="green",
    annotation_text="Excellent (95%)"
)

# Good threshold
fig_reserve_health.add_hline(
    y=90,
    line_dash="dot",
    line_color="gold",
    annotation_text="Good (90%)"
)

# Fair threshold
fig_reserve_health.add_hline(
    y=80,
    line_dash="dot",
    line_color="orange",
    annotation_text="Fair (80%)"
)

fig_reserve_health.update_layout(
    title="Monthly Reserve Adequacy Trend",
    xaxis_title="Month",
    yaxis_title="Reserve Adequacy (%)",
    yaxis=dict(
        range=[0, 100]
    ),
    height=450
)

st.plotly_chart(
    fig_reserve_health,
    use_container_width=True
)

st.caption(
    """
    Reserve Adequacy Legend:

    ≥95% = Excellent |
    90-94.9% = Good |
    80-89.9% = Fair |
    <80% = Poor

    Reserve Adequacy (%) =
    (Hours Meeting Reserve Requirement ÷ Total Hours) × 100
    """
)

# -----------------------------------------------------
# DETAIL TABLE
# -----------------------------------------------------

monthly_display = (
    monthly_summary[
        [
            "MonthName",
            "PeakDemand",
            "AverageDemand",
            "MaxShortage",
            "HoursWithShortage",
            "LowReserveHours",
            "ReserveAdequacyPct",
            "UnservedEnergy",
            "EnergyNotServedPct",
            "ReliabilityScore",
            "LoadFactor"
        ]
    ]
)

with st.expander(
    "Monthly Reliability Details",
    expanded=False
):

    st.dataframe(
        monthly_display.round({
            "PeakDemand": 2,
            "AverageDemand": 2,
            "MaxShortage": 2,
            "ReserveAdequacyPct": 1,
            "UnservedEnergy": 2,
            "EnergyNotServedPct": 3,
            "ReliabilityScore": 1,
            "LoadFactor": 1
        }),
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

# =====================================================
# CHART
# =====================================================

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

hourly_profile = total_demand.copy()

hourly_profile["Hour"] = (
    hourly_profile["Datetime"]
    .dt.hour
)

# -----------------------------------------------------
# COMMON Y-AXIS FOR BOTH BOXPLOTS
# -----------------------------------------------------
import math

# -----------------------------------------------------
# COMMON Y-AXIS FOR BOTH BOXPLOTS
# -----------------------------------------------------

import math

common_min = min(
    daily_peak["DailyPeak"].quantile(0.01),
    hourly_profile["Value"].quantile(0.01)
)

common_max = max(
    daily_peak["DailyPeak"].quantile(0.99),
    hourly_profile["Value"].quantile(0.99)
)

# Dynamic limits based on actual dataset
y_min = math.floor(common_min / 5) * 5
y_max = math.ceil(common_max / 5) * 5

# Dynamic tick interval
y_range = y_max - y_min

if y_range <= 50:
    y_tick = 5

elif y_range <= 100:
    y_tick = 10

elif y_range <= 200:
    y_tick = 20

else:
    y_tick = math.ceil(y_range / 10 / 5) * 5
    
# -----------------------------------------------------
# DAILY PEAK DEMAND BY MONTH
# -----------------------------------------------------

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

fig_peak.update_yaxes(
    range=[y_min, y_max],
    dtick=y_tick
)

with b1:
    st.plotly_chart(
        fig_peak,
        use_container_width=True
    )

# -----------------------------------------------------
# HOURLY DEMAND DISTRIBUTION
# -----------------------------------------------------

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

fig_hour.update_yaxes(
    range=[y_min, y_max],
    dtick=y_tick
)

with b2:
    st.plotly_chart(
        fig_hour,
        use_container_width=True
    )

st.caption(
    """
    The box-and-whisker plots summarize demand variability from two perspectives.
    Daily Peak Demand by Month shows how the daily system peak changes over time,
    highlighting seasonal patterns and peak-demand growth. Hourly Demand
    Distribution shows typical demand behavior by hour of day, revealing load
    patterns, peak periods, and variability. Both charts use a common MW scale
    to enable direct visual comparison across months and hours.
    """
)

# =====================================================
# Heatmap
# =====================================================

st.subheader(
    "Hour-Date Demand Heatmap (% of Peak Demand)"
)

heat_source = total_demand.copy()

heat_source["Date"] = (
    heat_source["Datetime"]
    .dt.strftime("%Y-%m-%d")
)

heat_source["Hour"] = (
    heat_source["Datetime"]
    .dt.hour
)

heat_source["DemandPctPeak"] = (
    heat_source["Value"]
    / peak_demand
    * 100
)

heat_tbl = (
    heat_source
    .pivot_table(
        index="Hour",
        columns="Date",
        values="DemandPctPeak",
        aggfunc="mean"
    )
)

fig_heat_demand = go.Figure(
    data=go.Heatmap(
        z=heat_tbl.values,
        x=heat_tbl.columns,
        y=heat_tbl.index,
        colorscale="RdYlGn_r",
        zmin=0,
        zmax=100,
        colorbar_title="% Peak"
    )
)

fig_heat_demand.update_layout(
    title="Demand Heatmap (% of System Peak)",
    xaxis_title="Date",
    yaxis_title="Hour",
    height=500
)

st.plotly_chart(
    fig_heat_demand,
    use_container_width=True
)

with st.expander(
    "View Heatmap Source Data",
    expanded=False
):
    st.dataframe(
        heat_tbl.round(1),
        use_container_width=True
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
    
segment_table = pd.DataFrame(segment_rows)

ldc_pct = (
    (ldc.index + 1)
    / len(ldc)
    * 100
)

st.caption("Load Segment Summary")

fig_elbow = go.Figure()

fig_elbow.add_trace(
    go.Scatter(
        x=sse_df["Segments"],
        y=sse_df["SSE"],
        mode="lines+markers",
        name="Total SSE"
    )
)

fig_elbow.add_trace(
    go.Scatter(
        x=[recommended_segments],
        y=[
            sse_df.loc[
                sse_df["Segments"] == recommended_segments,
                "SSE"
            ].iloc[0]
        ],
        mode="markers",
        marker=dict(
            size=14,
            color="red",
            symbol="star"
        ),
        name="Recommended"
    )
)

fig_elbow.update_layout(
    title="Elbow Method for Load Segmentation",
    xaxis_title="Number of Segments",
    yaxis_title="Segmentation SSE",
    height=400
)

selected_sse = float(total_sse)

recommended_sse = float(
    sse_df.loc[
        sse_df["Segments"] == recommended_segments,
        "SSE"
    ].iloc[0]
)

with st.expander(
    "Advanced LDC Segmentation Analysis",
    expanded=False
):

    st.metric(
        "Current Segmentation SSE",
        f"{selected_sse:,.0f}"
    )

    st.markdown(
        f"""
### Recommended Segmentation: {recommended_segments} Segments

The elbow analysis indicates that most of the reduction in
segmentation error is achieved by approximately
**{recommended_segments} segments**.

Beyond this point, additional segments improve accuracy
more slowly while increasing model complexity.

**Current Selection:** {num_segments} Segments
"""
    )

    if num_segments == recommended_segments:

        st.success(
            f"""
The current selection matches the recommended value.

A {num_segments}-segment model provides a balanced
representation of the Load Duration Curve while keeping
the segmentation simple enough for planning and dispatch
analysis.
"""
        )

    elif num_segments < recommended_segments:

        st.warning(
            f"""
The current selection is simpler than the recommended
{recommended_segments}-segment model.

While easier to interpret, some distinct demand regimes
may be merged together, resulting in higher SSE.
"""
        )

    else:

        improvement_pct = (
            (recommended_sse - selected_sse)
            / recommended_sse
            * 100
        )

        st.info(
            f"""
The current selection contains more segments than the
recommended {recommended_segments}-segment model.

This reduces SSE further but adds complexity.

Compared with the recommended segmentation,
error is reduced by approximately
{abs(improvement_pct):.1f}%.
"""
        )

    st.plotly_chart(
        fig_elbow,
        use_container_width=True
    )

    peak_segment = segment_table.iloc[0]
    base_segment = segment_table.iloc[-1]

    st.markdown(
        f"""
### Operational Interpretation

The selected **{num_segments}-segment** model divides
the annual Load Duration Curve into **{num_segments}
natural demand regimes**.

• Highest demand segment (**{peak_segment['Segment']}**) occurs during approximately **{peak_segment['% Time']:.1f}%** of the year.

• Lowest demand segment (**{base_segment['Segment']}**) occurs during approximately **{base_segment['% Time']:.1f}%** of the year.

• Total segmentation error is **{selected_sse:,.0f} SSE**.

• These segments can be used for dispatch planning,
capacity adequacy assessments, reserve studies,
and generation portfolio analysis.
"""
    )

    st.dataframe(
        segment_table,
        use_container_width=True,
        hide_index=True
    )

# ----------------------------------
# Load Duration Curve
# ----------------------------------

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


def get_segment_name(i, total_segments):
    if total_segments == 1:
        return "Load"

    if i == 0:
        return "Peaking"

    if i == total_segments - 1:
        return "Baseload"

    if total_segments == 3:
        return "Mid-Merit"

    return f"Mid-Merit {i}"


scale_factor = len(ldc) / len(ldc_seg)

segment_summary = []

for i, (start_idx, end_idx) in enumerate(boundaries):

    actual_start = int(start_idx * scale_factor)
    actual_end = int(end_idx * scale_factor)

    segment_data = ldc.iloc[actual_start:actual_end]

    if len(segment_data) == 0:
        continue

    segment_max = segment_data.max()
    segment_min = segment_data.min()

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

    duration_pct = end_pct - start_pct

    segment_name = get_segment_name(
        i,
        len(boundaries)
    )

    # Segment shading
    fig_ldc.add_vrect(
        x0=start_pct,
        x1=end_pct,
        fillcolor=segment_colors[
            i % len(segment_colors)
        ],
        opacity=0.12,
        line_width=0,
    )

    # Boundary line
    fig_ldc.add_vline(
        x=end_pct,
        line_dash="dot",
        line_color="black"
    )

    # Segment annotation
    fig_ldc.add_annotation(
        x=(start_pct + end_pct) / 2,
        y=segment_max,
        text=(
            f"<b>{segment_name}</b><br>"
            f"{segment_max:.1f} - "
            f"{segment_min:.1f} MW<br>"
            f"{duration_pct:.1f}%"
        ),
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        opacity=0.9
    )

    # Segment transition marker
    fig_ldc.add_trace(
        go.Scatter(
            x=[start_pct],
            y=[segment_max],
            mode="markers",
            marker=dict(
                size=10,
                color=segment_colors[
                    i % len(segment_colors)
                ]
            ),
            name=segment_name,
            hovertemplate=
                f"{segment_name}<br>"
                f"Max MW: {segment_max:.2f}<br>"
                f"Duration: {duration_pct:.2f}%"
                "<extra></extra>"
        )
    )

    segment_summary.append({
    "Segment": segment_name,
    "MW Range":
        f"{segment_max:.2f} - {segment_min:.2f}",
    "Duration %": round(duration_pct, 2)
})

# Average load
fig_ldc.add_hline(
    y=average_load,
    line_dash="dash",
    annotation_text=
        f"Average Load ({average_load:,.2f} MW)"
)

# Peak demand marker
fig_ldc.add_annotation(
    x=0,
    y=ldc.max(),
    text=(
        f"Peak Demand<br>"
        f"{ldc.max():,.2f} MW"
    ),
    showarrow=True,
    arrowhead=2
)

# Minimum demand marker
fig_ldc.add_annotation(
    x=100,
    y=ldc.min(),
    text=(
        f"Minimum Demand<br>"
        f"{ldc.min():,.2f} MW"
    ),
    showarrow=True,
    arrowhead=2
)

fig_ldc.update_layout(
    title=f"Load Duration Curve ({num_segments} Segments)",
    xaxis_title="Percent of Time Exceeded (%)",
    yaxis_title="Demand (MW)",
    height=600,
    hovermode="x unified",
    legend_title="Segment"
)

st.plotly_chart(
    fig_ldc,
    use_container_width=True
)

# ----------------------------------
# Segment Summary Table
# ----------------------------------

st.markdown(
    "##### Segment Summary"
)

st.dataframe(
    pd.DataFrame(segment_summary),
    use_container_width=True,
    hide_index=True
)

# ----------------------------------
# RESERVE SECURITY ASSESSMENT
# ----------------------------------

st.subheader(
    "Reserve Security Assessment"
)

total_hours = len(gap_df)

unserved_hours = (
    gap_df["ShortageMW"]
    >= SHORTAGE_THRESHOLD
).sum()

served_hours = (
    total_hours
    - unserved_hours
)

served_pct = (
    served_hours
    / total_hours
    * 100
)

served_df = gap_df[
    gap_df["ShortageMW"]
    < SHORTAGE_THRESHOLD
].copy()

hours_meeting_reserve = (
    served_df["ReserveMargin"]
    >= served_df["RequiredReserve"]
).sum()

hours_below_reserve = (
    served_df["ReserveMargin"]
    < served_df["RequiredReserve"]
).sum()

reserve_compliance_pct = (
    hours_meeting_reserve
    / max(served_hours, 1)
    * 100
)

worst_reserve_deficiency = (
    served_df["ReserveMargin"]
    -
    served_df["RequiredReserve"]
).min()

# ----------------------------------
# DESCRIPTION
# ----------------------------------

st.caption(
    """
    This assessment focuses on hours where customer
    demand was successfully served.

    Reserve adequacy is evaluated against the operating
    reserve requirement consisting of:

    • 2.8% Regulating / Load-Following Reserve

    • 10% Contingency Reserve based on Total
      Synchronized Generation

    Hours with unserved demand are excluded from this
    assessment and are reported separately in the
    Reliability Health Monitor.
    """
)

# ----------------------------------
# AVERAGE RESERVE REQUIREMENTS
# ----------------------------------

avg_regulating = (
    gap_df["RegulatingReserve"]
    .mean()
)

avg_contingency = (
    gap_df["ContingencyReserve"]
    .mean()
)

avg_required = (
    gap_df["RequiredReserve"]
    .mean()
)

r1, r2, r3 = st.columns(3)

with r1:
    st.metric(
        "Avg Regulating Reserve",
        f"{avg_regulating:.2f} MW"
    )

with r2:
    st.metric(
        "Avg Contingency Reserve",
        f"{avg_contingency:.2f} MW"
    )

with r3:
    st.metric(
        "Avg Total Required Reserve",
        f"{avg_required:.2f} MW"
    )



# ----------------------------------
# STUDY PERIOD SUMMARY
# ----------------------------------

s1, s2, s3, s4 = st.columns(4)

with s1:
    st.metric(
        "Hours Evaluated",
        f"{total_hours:,.0f}"
    )

with s2:
    st.metric(
        "Unserved Hours",
        f"{unserved_hours:,.0f}"
    )

with s3:
    st.metric(
        "Demand Served Hours",
        f"{served_hours:,.0f}"
    )

with s4:
    st.metric(
        "Served Hours %",
        f"{served_pct:.1f}%"
    )

st.markdown("---")

# ----------------------------------
# RESERVE SECURITY KPI
# ----------------------------------

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        "Reserve Compliance",
        f"{reserve_compliance_pct:.1f}%"
    )

with k2:
    st.metric(
        "Hours Meeting Requirement",
        f"{hours_meeting_reserve:,.0f}"
    )

with k3:
    st.metric(
        "Hours Below Requirement",
        f"{hours_below_reserve:,.0f}"
    )

with k4:
    st.metric(
        "Worst Reserve Deficiency",
        f"{worst_reserve_deficiency:,.2f} MW"
    )

# ----------------------------------
# RESERVE REQUIREMENT CALCULATION
# ----------------------------------

with st.expander(
    "How Reserve Requirement Was Calculated",
    expanded=False
):

    inspect_df = gap_df.copy()

    selected_hour = st.selectbox(
        "Select Hour",
        inspect_df["Datetime"]
        .sort_values()
        .dt.strftime("%Y-%m-%d %H:%M")
    )

    row = inspect_df[
        inspect_df["Datetime"].dt.strftime("%Y-%m-%d %H:%M")
        == selected_hour
    ].iloc[0]

    reserve_status = (
        "✅ COMPLIANT"
        if row["ReserveMargin"] >= row["RequiredReserve"]
        else "❌ DEFICIENT"
    )

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "Demand",
            f"{row['TotalDemand'\]:.2f} MW"
        )

    with b:
        st.metric(
            "Generation",
            f"{row['TotalGeneration'\]:.2f} MW"
        )

    with c:
        st.metric(
            "Reserve Margin",
            f"{row['ReserveMargin'\]:.2f} MW"
        )

    with d:
        st.metric(
            "Required Reserve",
            f"{row['RequiredReserve'\]:.2f} MW"
        )

    st.markdown("---")

    st.markdown(
        f"""
### Calculation

**Regulating Reserve**

= Demand × 2.8%

= {row['TotalDemand'\]:.2f} × 2.8%

= **{row['RegulatingReserve'\]:.2f} MW**

**Contingency Reserve**

= Generation × 10%

= {row['TotalGeneration'\]:.2f} × 10%

= **{row['ContingencyReserve'\]:.2f} MW**

**Required Reserve**

= Regulating Reserve + Contingency Reserve

= {row['RegulatingReserve'\]:.2f}
+ {row['ContingencyReserve'\]:.2f}

= **{row['RequiredReserve'\]:.2f} MW**

**Actual Reserve Margin**

= Supply − Demand

= **{row['ReserveMargin'\]:.2f} MW**

### Result

{reserve_status}
"""
    )

# ----------------------------------
# OPERATING CONDITION BREAKDOWN
# ----------------------------------

adequate_hours = hours_meeting_reserve

reserve_deficient_hours = hours_below_reserve

fig_reserve_breakdown = go.Figure()

fig_reserve_breakdown.add_trace(
    go.Bar(
        y=["Study Period"],
        x=[adequate_hours],
        name="Adequate Reserve",
        orientation="h",
        marker_color="green",
        text=[
            f"{adequate_hours:,}"
        ],
        textposition="inside"
    )
)

fig_reserve_breakdown.add_trace(
    go.Bar(
        y=["Study Period"],
        x=[reserve_deficient_hours],
        name="Reserve Deficient",
        orientation="h",
        marker_color="orange",
        text=[
            f"{reserve_deficient_hours:,}"
        ],
        textposition="inside"
    )
)

fig_reserve_breakdown.add_trace(
    go.Bar(
        y=["Study Period"],
        x=[unserved_hours],
        name="Unserved Demand",
        orientation="h",
        marker_color="red",
        text=[
            f"{unserved_hours:,}"
        ],
        textposition="inside"
    )
)

fig_reserve_breakdown.update_layout(
    title="Operating Condition Breakdown",
    barmode="stack",
    xaxis_title="Hours",
    height=350
)

st.plotly_chart(
    fig_reserve_breakdown,
    use_container_width=True
)

# ----------------------------------
# MONTHLY RESERVE COMPLIANCE TREND
# ----------------------------------

reserve_monthly = gap_df.copy()

reserve_monthly["Month"] = (
    reserve_monthly["Datetime"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

reserve_monthly["MonthLabel"] = (
    reserve_monthly["Datetime"]
    .dt.strftime("%b %Y")
)

reserve_monthly["ServedFlag"] = (
    reserve_monthly["ShortageMW"]
    < SHORTAGE_THRESHOLD
)

reserve_monthly["ReserveCompliant"] = (
    (
        reserve_monthly["ReserveMargin"]
        >= reserve_monthly["RequiredReserve"]
    )
    &
    reserve_monthly["ServedFlag"]
)

monthly_reserve = (
    reserve_monthly
    .groupby(
        ["Month", "MonthLabel"],
        as_index=False
    )
    .agg(
        ServedHours=(
            "ServedFlag",
            "sum"
        ),
        CompliantHours=(
            "ReserveCompliant",
            "sum"
        )
    )
)

monthly_reserve["ReserveCompliancePct"] = (
    monthly_reserve["CompliantHours"]
    /
    monthly_reserve["ServedHours"]
    .replace(0, pd.NA)
    * 100
)

monthly_reserve = (
    monthly_reserve
    .sort_values("Month")
)

fig_reserve_trend = go.Figure()

fig_reserve_trend.add_trace(
    go.Scatter(
        x=monthly_reserve["MonthLabel"],
        y=monthly_reserve[
            "ReserveCompliancePct"
        ],
        mode="lines+markers+text",
        text=(
            monthly_reserve[
                "ReserveCompliancePct"
            ]
            .round(1)
            .astype(str)
            + "%"
        ),
        textposition="top center",
        line=dict(
            width=3,
            color="#1565C0"
        )
    )
)

fig_reserve_trend.add_hline(
    y=95,
    line_dash="dash",
    line_color="green",
    annotation_text="Excellent"
)

fig_reserve_trend.add_hline(
    y=90,
    line_dash="dot",
    line_color="gold",
    annotation_text="Good"
)

fig_reserve_trend.add_hline(
    y=80,
    line_dash="dot",
    line_color="orange",
    annotation_text="Fair"
)

fig_reserve_trend.update_layout(
    title="Monthly Reserve Compliance Trend",
    xaxis_title="Month",
    yaxis_title="Reserve Compliance (%)",
    yaxis=dict(
        range=[0, 100]
    ),
    height=450
)

st.plotly_chart(
    fig_reserve_trend,
    use_container_width=True
)

# ----------------------------------
# RESERVE DEFICIENT HOURS DETAIL
# ----------------------------------

reserve_detail = served_df[
    served_df["ReserveMargin"]
    < served_df["RequiredReserve"]
].copy()

reserve_detail["ReserveDeficiency"] = (
    reserve_detail["ReserveMargin"]
    -
    reserve_detail["RequiredReserve"]
)

# Worst reserve violations first
reserve_detail = (
    reserve_detail
    .sort_values(
        "ReserveDeficiency",
        ascending=True
    )
    .reset_index(drop=True)
)

# Add ranking
reserve_detail.insert(
    0,
    "Rank",
    range(
        1,
        len(reserve_detail) + 1
    )
)

reserve_detail = reserve_detail[
    [
        "Rank",
        "Datetime",
        "TotalDemand",
        "TotalSupply",
        "ReserveMargin",
        "RequiredReserve",
        "ReserveDeficiency"
    ]
]

with st.expander(
    "View Reserve Deficient Hours",
    expanded=False
):

    st.dataframe(
        reserve_detail.round({
            "TotalDemand": 2,
            "TotalSupply": 2,
            "ReserveMargin": 2,
            "RequiredReserve": 2,
            "ReserveDeficiency": 2
        }),
        use_container_width=True,
        hide_index=True
    )

# ----------------------------------
# Shortage Event Analysis
# ----------------------------------

st.subheader("Shortage Event Analysis")

monthly_shortage = (
    gap_df.assign(
        MonthDate=gap_df["Datetime"].dt.to_period("M").dt.to_timestamp(),
        MonthLabel=gap_df["Datetime"].dt.strftime("%b %Y")
    )
    .groupby(
        ["MonthDate", "MonthLabel"],
        as_index=False
    )
    .agg(
        UnservedEnergy=(
            "ShortageMW",
            lambda x: x.clip(lower=0).sum()
        ),
        ShortageHours=(
            "ShortageMW",
            lambda x: (
                x >= SHORTAGE_THRESHOLD
            ).sum()
        ),
        MaxShortageMW=(
            "ShortageMW",
            "max"
        )
    )
    .sort_values("MonthDate")
)

import plotly.express as px

fig_monthly_shortage = px.scatter(
    monthly_shortage,
    x="MonthLabel",
    y="UnservedEnergy",
    size="ShortageHours",
    color="MaxShortageMW",
    text="MonthLabel",
    color_continuous_scale="Reds",
    size_max=60
)

fig_monthly_shortage.update_traces(
    textposition="top center"
)

fig_monthly_shortage.update_layout(
    title="Monthly Reliability Impact Overview",
    xaxis_title="Month",
    yaxis_title="Unserved Energy (MWh)",
    height=600
)

st.plotly_chart(
    fig_monthly_shortage,
    use_container_width=True
)

worst_month = (
    monthly_shortage.sort_values(
        "UnservedEnergy",
        ascending=False
    ).iloc[0]
)

st.info(
    f"""
Worst Reliability Month: {worst_month['MonthLabel']}

• Unserved Energy: {worst_month['UnservedEnergy']:.2f} MWh
• Shortage Hours: {worst_month['ShortageHours']}
• Maximum Shortage: {worst_month['MaxShortageMW']:.2f} MW
"""
)

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

if len(shortage_events) > 0:

    shortage_events["Month"] = (
        pd.to_datetime(
            shortage_events["Start"]
        )
        .dt.strftime("%b %Y")
    )

    shortage_events = (
        shortage_events
        .sort_values(
            "Unserved Energy MWh",
            ascending=False
        )
        .reset_index(drop=True)
    )

    shortage_events.insert(
        0,
        "Event Number",
        range(
            1,
            len(shortage_events) + 1
        )
    )

    largest_event = (
        shortage_events.iloc[0]
    )

    longest_event = (
        shortage_events.loc[
            shortage_events[
                "Duration Hours"
            ].idxmax()
        ]
    )

    highest_shortage = (
        shortage_events.loc[
            shortage_events[
                "Max Shortage MW"
            ].idxmax()
        ]
    )

    e1, e2, e3 = st.columns(3)

    with e1:
        st.metric(
            "Largest Event",
            f"{largest_event['Unserved Energy MWh']:,.2f} MWh"
        )
        st.caption(
            f"{largest_event['Month']}"
        )

    with e2:
        st.metric(
            "Longest Event",
            f"{longest_event['Duration Hours']:,.0f} hrs"
        )
        st.caption(
            f"{longest_event['Month']}"
        )

    with e3:
        st.metric(
            "Highest Shortage",
            f"{highest_shortage['Max Shortage MW']:,.2f} MW"
        )
        st.caption(
            f"{highest_shortage['Month']}"
        )

    shortage_events_display = (
        shortage_events[
            [
                "Event Number",
                "Month",
                "Start",
                "End",
                "Duration Hours",
                "Max Shortage MW",
                "Unserved Energy MWh"
            ]
        ]
    )

    with st.expander(
        "View Shortage Event Data",
        expanded=False
    ):
        st.dataframe(
            shortage_events_display.round({
                "Duration Hours": 0,
                "Max Shortage MW": 2,
                "Unserved Energy MWh": 2
            }),
            height=350,
            use_container_width=True,
            hide_index=True
        )

# =====================================================
# Plant Contribution Analysis
# =====================================================

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

c1, c2 = st.columns([3, 1])

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
        height=650
    )

    st.plotly_chart(
        fig_tree,
        use_container_width=True
    )

with c2:

    st.markdown("##### Plant Contribution Data")

    st.dataframe(
        plant_summary[
            [
                "Plant",
                "Contribution %",
                "EnergyMWh",
            ]
        ].round(2),
        use_container_width=True,
        hide_index=True,
        height=650
    )

# =====================================================
# OPTION 2 - PLANT ROLE MATRIX
# =====================================================

st.subheader(
    "Plant Role Matrix"
)

st.markdown(
    """
**How to Read This Chart**

• Higher = larger annual energy contribution

• Further right = larger contribution during peak-demand periods

• Larger bubbles = larger average generation output

**Quadrants**

🟩 Upper Right = Core System Assets (high energy + high peak support)

🟦 Upper Left = Baseload-Oriented Assets (high energy, lower peak support)

🟨 Lower Right = Peaking Assets (critical during peaks, lower annual energy)

🟥 Lower Left = Support Assets (limited contribution to both energy and peak demand)
"""
)

peak_threshold = peak_demand * 0.90

peak_hours = total_demand.loc[
    total_demand["Value"] >= peak_threshold,
    "Datetime"
]

# Annual energy contribution

energy_share = (
    generation
    .groupby("Plant", as_index=False)
    .agg(
        EnergyMWh=("Value", "sum"),
        AvgMW=("Value", "mean")
    )
)

energy_share["EnergyContributionPct"] = (
    energy_share["EnergyMWh"]
    /
    energy_share["EnergyMWh"].sum()
    * 100
)

# Peak-period contribution

peak_gen = generation[
    generation["Datetime"].isin(peak_hours)
]

peak_share = (
    peak_gen
    .groupby("Plant", as_index=False)
    .agg(
        PeakEnergyMWh=("Value", "sum")
    )
)

peak_share["PeakContributionPct"] = (
    peak_share["PeakEnergyMWh"]
    /
    peak_share["PeakEnergyMWh"].sum()
    * 100
)

role_df = energy_share.merge(
    peak_share[
        [
            "Plant",
            "PeakContributionPct"
        ]
    ],
    on="Plant",
    how="left"
)

role_df["PeakContributionPct"] = (
    role_df["PeakContributionPct"]
    .fillna(0)
)

fig_role = px.scatter(
    role_df,
    x="PeakContributionPct",
    y="EnergyContributionPct",
    size="AvgMW",
    color="Plant",
    text="Plant",
    size_max=70
)

fig_role.update_traces(
    textposition="top center"
)

fig_role.update_layout(
    title="Plant Role Matrix",
    xaxis_title="Peak Demand Contribution (%)",
    yaxis_title="Annual Energy Contribution (%)",
    height=700
)

median_energy = role_df["EnergyContributionPct"].median()
median_peak = role_df["PeakContributionPct"].median()

fig_role.add_hline(
    y=median_energy,
    line_dash="dash",
    line_color="gray"
)

fig_role.add_vline(
    x=median_peak,
    line_dash="dash",
    line_color="gray"
)

fig_role.add_annotation(
    x=median_peak * 0.5,
    y=median_energy * 1.5,
    text="BASELOAD",
    showarrow=False,
    opacity=0.5
)

fig_role.add_annotation(
    x=median_peak * 1.6,
    y=median_energy * 1.5,
    text="CORE ASSETS",
    showarrow=False,
    opacity=0.5
)

fig_role.add_annotation(
    x=median_peak * 1.6,
    y=median_energy * 0.4,
    text="PEAKING",
    showarrow=False,
    opacity=0.5
)

fig_role.add_annotation(
    x=median_peak * 0.5,
    y=median_energy * 0.4,
    text="SUPPORT",
    showarrow=False,
    opacity=0.5
)


st.plotly_chart(
    fig_role,
    use_container_width=True
)

with st.expander(
    "View Plant Role Matrix Data",
    expanded=False
):
    st.dataframe(
        role_df[
            [
                "Plant",
                "EnergyMWh",
                "AvgMW",
                "EnergyContributionPct",
                "PeakContributionPct"
            ]
        ]
        .sort_values(
            "EnergyContributionPct",
            ascending=False
        )
        .round(2),
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

with st.expander(
    "View Generation Mix at Peak Demand Data",
    expanded=False
):
    st.dataframe(
        peak_mix_display.round({
            "Value": 2,
            "Percent": 2
        }),
        use_container_width=True,
        hide_index=True
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
            "INSTALLED CAPACITY (MW)",
            "DEPENDABLE CAPACITY"
        ]
    )
].copy()

capacity_data["Attribute"] = (
    capacity_data["Attribute"]
    .astype(str)
    .str.upper()
)

# -----------------------------------------------------
# CAPACITY SCENARIO
# -----------------------------------------------------

st.sidebar.subheader(
    "Capacity Scenario"
)

retired_plants = st.sidebar.multiselect(
    "Scenario: Retired / Unavailable Plants",
    options=sorted(
        capacity_data["Plant"]
        .dropna()
        .unique()
    ),
    default=[]
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

cap_check = (
    capacity_data[
        capacity_data["Attribute"]
        .eq(
            "DEPENDABLE CAPACITY"
        )
    ]
    .groupby(
        ["Plant", "Unit"],
        as_index=False
    )
    .agg(
        DependableMW=("Value", "max")
    )
)

cap_check["Retired"] = (
    cap_check["Plant"]
    .isin(retired_plants)
)

available_capacity = (
    cap_check.loc[
        ~cap_check["Retired"],
        "DependableMW"
    ]
    .sum()
)

removed_capacity = (
    cap_check.loc[
        cap_check["Retired"],
        "DependableMW"
    ]
    .sum()
)

removed_capacity_tbl = (
    cap_check[
        cap_check["Retired"]
    ]
    .groupby(
        "Plant",
        as_index=False
    )
    .agg(
        RemovedMW=("DependableMW", "sum")
    )
    .sort_values(
        "RemovedMW",
        ascending=False
    )
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

if reserve_margin_pct >= 20:
    planning_risk = "Low Risk"

elif reserve_margin_pct >= 10:
    planning_risk = "Moderate Risk"

elif reserve_margin_pct >= 0:
    planning_risk = "High Risk"

else:
    planning_risk = "Capacity Deficit"

# -----------------------------------------------------
# OUTLOOK KPIs
# -----------------------------------------------------

scenario_text = (
    ", ".join(retired_plants)
    if len(retired_plants) > 0
    else "Base Case"
)

st.subheader(
    f"Demand Growth & Capacity Outlook "
    f"(@ {growth_rate:.1f}% Annual Growth)"
)

st.caption(
    f"Scenario: {scenario_text}"
)

f1, f2, f3, f4, f5 = st.columns(5)

with f1:
    st.metric(
        "Current Peak Demand",
        f"{peak_demand:,.2f} MW"
    )

with f2:
    st.metric(
        "Projected Peak Demand",
        f"{projected_peak:,.2f} MW"
    )

with f3:
    st.metric(
        "Available Capacity",
        f"{available_capacity:,.2f} MW"
    )

with f4:
    st.metric(
        "Removed Capacity",
        f"{removed_capacity:,.2f} MW"
    )

with f5:
    st.metric(
        "Reserve Margin",
        f"{reserve_margin_pct:.1f}%"
    )

st.metric(
    "Additional Capacity Needed",
    f"{required_new_capacity:,.2f} MW"
)

# -----------------------------------------------------
# INTERPRETATION
# -----------------------------------------------------

if planning_risk == "Low Risk":

    st.success(
        "Low Risk: Capacity remains sufficient under the selected scenario."
    )

elif planning_risk == "Moderate Risk":

    st.info(
        "Moderate Risk: Capacity remains adequate but planning reserves are reduced."
    )

elif planning_risk == "High Risk":

    st.warning(
        "High Risk: Limited planning reserve remains under the selected scenario."
    )

else:

    st.error(
        "Capacity Deficit: Additional capacity is required."
    )

# -----------------------------------------------------
# CROSS-CHECK TABLE
# -----------------------------------------------------

with st.expander(
    "View Dependable Capacity Assumptions",
    expanded=False
):

    st.dataframe(
        cap_check.sort_values(
            ["Plant", "Unit"]
        ),
        use_container_width=True,
        hide_index=True
    )

    if len(removed_capacity_tbl) > 0:

        st.markdown(
            "##### Removed Plants"
        )

        st.dataframe(
            removed_capacity_tbl,
            use_container_width=True,
            hide_index=True
        )

    st.write(
        f"Total Dependable Capacity: "
        f"{cap_check['DependableMW'].sum():.2f} MW"
    )

    st.write(
        f"Remaining Capacity: "
        f"{available_capacity:.2f} MW"
    )

    st.write(
        f"Removed Capacity: "
        f"{removed_capacity:.2f} MW"
    )

# -----------------------------------------------------
# 10-YEAR OUTLOOK TABLE
# -----------------------------------------------------

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

        "Projected Peak MW":
            round(projected, 2),

        "Capacity Margin MW":
            round(reserve, 2),

        "Additional Capacity Needed MW":
            round(
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

fig = go.Figure()

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
    title="Palawan Dispatch",
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
    filtered[
        filtered["Attribute"]
        .astype(str)
        .str.upper()
        .eq("OUTPUT")
    ]
)

peak_snapshot = peak_snapshot[
    peak_snapshot["Datetime"].isin(peak_hours)
]

peak_snapshot = (
    peak_snapshot
    .groupby(
        ["Plant","Unit"],
        as_index=False
    )
    .agg(
        AvgPeakMW=("Value","mean"),
        MaxPeakMW=("Value","max"),
        PeakEnergyMWh=("Value","sum")
    )
)

peak_snapshot["PlantUnit"] = (
    peak_snapshot["Plant"]
    + " | "
    + peak_snapshot["Unit"].astype(str)
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

with st.expander(
    "Peak Hour Snapshot (90%-100% of Peak Demand)",
    expanded=False
):
    st.dataframe(
        peak_snapshot[
            [
                "Plant",
                "Unit",
                "AvgPeakMW",
                "MaxPeakMW",
                "PeakEnergyMWh",
                "PeakEnergyShare %"
            ]
        ],
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

# aggregate to PLANT level
daily_peak_gen = (
    daily_peak_gen
    .groupby(
        ["Datetime", "Plant"],
        as_index=False
    )
    .agg(
        Value=("Value", "sum")
    )
)

# calculate total system generation for each peak hour
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

plant_order = (
    daily_peak_gen
    .groupby("Plant")["Value"]
    .sum()
    .sort_values(ascending=False)
    .index
    .tolist()
)

for plant in plant_order:

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

available_capacity_tbl = (
    capacity_data[
        capacity_data["Attribute"]
        .isin(
            [
                "DEPENDABLE CAPACITY",
                "INSTALLED CAPACITY (MW)"
            ]
        )
    ]
    .pivot_table(
        index=["Plant", "Unit"],
        columns="Attribute",
        values="Value",
        aggfunc="max"
    )
    .reset_index()
)

available_capacity_tbl.rename(
    columns={
        "DEPENDABLE CAPACITY": "DependableMW",
        "INSTALLED CAPACITY (MW)": "InstalledMW"
    },
    inplace=True
)

available_capacity_tbl["AvailableMW"] = (
    available_capacity_tbl["DependableMW"]
)

# -----------------------------------------------------
# PERFORMANCE TABLE
# -----------------------------------------------------

performance = peak_snapshot.merge(
    available_capacity_tbl,
    on=["Plant","Unit"],
    how="left"
)

performance["Peak Support %"] = (
    performance["MaxPeakMW"]
    /
    performance["DependableMW"]
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

    available = row["AvailableMW"]
    ach = row["Peak Support %"]

    if pd.isna(available):
        return "No Data"

    if available <= 0:
        return "Unavailable"

    plant = str(row["Plant"]).upper()

    if "MHP" in plant:

        if ach >= 70:
            return "OK"

        if ach >= 40:
            return "Monitor"

        return "Underperforming"

    else:

        if ach >= 90:
            return "OK"

        if ach >= 70:
            return "Monitor"

        return "Underperforming"

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

    if row["Risk Flag"] == "Unavailable":

        return (
            "Unit unavailable during the analysis period. "
            "Performance assessment is not applicable."
        )

    if row["Risk Flag"] == "OK":

        return (
            "Unit achieved expected capability "
            "during peak-demand periods."
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

    if row["Risk Flag"] == "Underperforming":

        if "MHP" in plant:

            return (
                "Unit was available but did not achieve "
                "expected hydro output during peak periods."
            )

        return (
            "Unit was available but did not achieve "
            "expected capability. Review derating, "
            "maintenance history, fuel supply, and "
            "dispatch restrictions."
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
   **Story:** Evaluates whether individual generating units
achieved their available capability during critical
demand periods.
    """
)

with st.expander(
    "View Peak Hour Performance Table",
    expanded=False
):
    st.dataframe(
        performance[
            [
                "Plant",
                "Unit",
                "DependableMW",
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
    "Underperforming": "red",
    "Unavailable": "gray",
    "No Data": "lightgray"
}

fig_perf = go.Figure()

for flag in performance["Risk Flag"].unique():

    temp = performance[
        performance["Risk Flag"] == flag
    ]

    fig_perf.add_trace(
    go.Bar(
        y=temp["PlantUnit"],
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
    "Unit Peak Support During Critical Hours"
    "(Max Peak MW / Dependable MW)"
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

st.caption(
    """
    Capability Realization (%) =
    Maximum Observed Output ÷ Dependable Capacity

    Utilization Factor (%) =
    Average Output ÷ Dependable Capacity

    Sustained Capability (%) =
    Operating Hours Above 80% of Dependable Capacity
    ÷ Total Operating Hours

    Interpretation:
    • High Capability Realization = unit can reach its rated capability.
    • High Utilization Factor = unit is heavily utilized.
    • High Sustained Capability = unit can maintain strong output consistently,
      not just during isolated peak events.
    """
)

# -----------------------------------------------------
# AVAILABLE CAPACITY
# -----------------------------------------------------

dependable_capacity_tbl = (
    capacity_data[
        capacity_data["Attribute"]
        .str.contains(
            "DEPENDABLE CAPACITY",
            na=False
        )
    ]
    .groupby(
        ["Plant","Unit"],
        as_index=False
    )
    .agg(
        DependableMW=("Value","max")
    )
)

dependable_capacity_tbl = (
    dependable_capacity_tbl
    .groupby("Plant", as_index=False)
    .agg(
        DependableMW=("DependableMW","sum")
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
        return "Unavailable"

    if realization >= 95:
        return "OK"

    if realization >= 75:
        return "Monitor"

    return "Underperforming"

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

    if row["Risk Flag"] == "Unavailable":
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

with st.expander(
    "View Plant Asset Performance Table",
    expanded=False
):
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
    "Underperforming": "red",
    "Unavailable": "gray",
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

st.markdown(
    """
    **Story:** Evaluates whether individual units can
    consistently sustain at least 80% of their
    dependable capacity throughout the
    study period, rather than merely reaching full
    output on isolated occasions.
    """
)

if "Unit" not in df.columns:

    st.warning(
        "Column 'Unit' not found."
    )

else:

    # -------------------------------------------------
    # HOURLY UNIT GENERATION
    # -------------------------------------------------

    unit_hourly = (
        filtered[
            filtered["Attribute"]
            .astype(str)
            .str.upper()
            .eq("OUTPUT")
        ]
        .groupby(
            ["Datetime","Plant","Unit"],
            as_index=False
        )
        .agg(
            MW=("Value","sum")
        )
    )

    # -------------------------------------------------
    # DEPENDABLE CAPACITY
    # -------------------------------------------------

    unit_dependable = (
        filtered[
            filtered["Attribute"]
            .astype(str)
            .str.upper()
            .eq(
                "DEPENDABLE CAPACITY"
            )
        ]
        .groupby(
            ["Plant","Unit"],
            as_index=False
        )
        .agg(
            DependableMW=("Value","max")
        )
    )

    # -------------------------------------------------
    # UNIT STATISTICS
    # -------------------------------------------------

    unit_perf = (
        unit_hourly
        .groupby(
            ["Plant","Unit"],
            as_index=False
        )
        .agg(
            AvgMW=("MW","mean"),
            MaxObservedMW=("MW","max"),
            EnergyMWh=("MW","sum"),
            OperatingHours=(
                "MW",
                lambda x: (x > 0).sum()
            )
        )
    )

    unit_perf = unit_perf.merge(
        unit_dependable,
        on=["Plant","Unit"],
        how="left"
    )

    # -------------------------------------------------
    # HOURS ABOVE 80% DEPENDABLE
    # -------------------------------------------------

    hourly_cap = (
        unit_hourly.merge(
            unit_dependable,
            on=["Plant","Unit"],
            how="left"
        )
    )

    hourly_cap["Above80Pct"] = (
        hourly_cap["MW"]
        >=
        hourly_cap["DependableMW"] * 0.80
    )

    sustained_tbl = (
        hourly_cap
        .groupby(
            ["Plant","Unit"],
            as_index=False
        )
        .agg(
            HoursAbove80Pct=(
                "Above80Pct",
                "sum"
            )
        )
    )

    unit_perf = unit_perf.merge(
        sustained_tbl,
        on=["Plant","Unit"],
        how="left"
    )

    # -------------------------------------------------
    # KPIs
    # -------------------------------------------------

    unit_perf["CapabilityRealization %"] = (
        unit_perf["MaxObservedMW"]
        /
        unit_perf["DependableMW"]
        * 100
    )

    unit_perf["UtilizationFactor %"] = (
        unit_perf["AvgMW"]
        /
        unit_perf["DependableMW"]
        * 100
    )

    unit_perf["SustainedCapability %"] = (
        unit_perf["HoursAbove80Pct"]
        /
        unit_perf["OperatingHours"]
        * 100
    )

    # -------------------------------------------------
    # RISK FLAG
    # -------------------------------------------------

    def get_unit_flag(row):

        if pd.isna(row["DependableMW"]):
            return "No Data"

        if row["DependableMW"] <= 0:
            return "Unavailable"

        if row["SustainedCapability %"] >= 80:
            return "OK"

        if row["SustainedCapability %"] >= 40:
            return "Monitor"

        return "Underperforming"


    unit_perf["Risk Flag"] = (
        unit_perf.apply(
            get_unit_flag,
            axis=1
        )
    )

    # -------------------------------------------------
    # REMARKS
    # -------------------------------------------------

    def unit_remark(row):

        if row["Risk Flag"] == "OK":
            return (
                "Frequently sustains at least 80% of dependable capacity."
            )

        if row["Risk Flag"] == "Monitor":
            return (
                "Moderate sustained capability. Performance should be monitored."
            )

        if row["Risk Flag"] == "Underperforming":
            return (
                "Unit was available but rarely sustained dependable capability. "
                "Review outages, derating, maintenance, fuel supply, or dispatch strategy."
            )

        if row["Risk Flag"] == "Unavailable":
            return (
                "Unit unavailable during the analysis period."
            )

        return "Missing data."


    unit_perf["Remarks"] = (
        unit_perf.apply(
            unit_remark,
            axis=1
        )
    )

    unit_perf["PlantUnit"] = (
        unit_perf["Plant"]
        + " | "
        + unit_perf["Unit"].astype(str)
    )

    unit_perf = unit_perf.sort_values(
        ["Plant", "SustainedCapability %"],
        ascending=[True, True]
    )
    
    # -------------------------------------------------
    # TABLE
    # -------------------------------------------------

    with st.expander(
        "View Unit Capability Realization Table",
        expanded=False
    ):
        st.dataframe(
            unit_perf[
                [
                    "Plant",
                    "Unit",
                    "DependableMW",
                    "AvgMW",
                    "MaxObservedMW",
                    "OperatingHours",
                    "HoursAbove80Pct",
                    "UtilizationFactor %",
                    "CapabilityRealization %",
                    "SustainedCapability %",
                    "Risk Flag",
                    "Remarks"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    # -------------------------------------------------
    # CHART
    # -------------------------------------------------

    color_map = {
        "OK": "green",
        "Monitor": "gold",
        "Underperforming": "red",
        "Unavailable": "gray",
        "No Data": "lightgray"
    }

    fig_unit = go.Figure()

    for flag in unit_perf["Risk Flag"].unique():

        temp = unit_perf[
            unit_perf["Risk Flag"] == flag
        ]

        fig_unit.add_trace(
            go.Bar(
                y=temp["PlantUnit"],
                x=temp["SustainedCapability %"],
                orientation="h",
                name=flag,
                marker_color=color_map.get(
                    flag,
                    "blue"
                )
            )
        )

    fig_unit.add_vline(
        x=80,
        line_dash="dash",
        line_color="green"
    )

    fig_unit.add_vline(
        x=40,
        line_dash="dash",
        line_color="orange"
    )

    fig_unit.update_layout(
        title="Unit Sustained Capability Assessment",
        xaxis_title=
            "% of Operating Hours Above 80% of Dependable Capacity",
        yaxis_title="Plant | Unit",
        height=max(
            700,
            len(unit_perf) * 30
        ),
        barmode="group"
    )

    st.plotly_chart(
        fig_unit,
        use_container_width=True
    )
