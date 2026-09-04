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
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "Upload mindoro dispatch.csv",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Please upload mindoro dispatch.csv")
    st.stop()

# =====================================================
# LOAD DATA
# =====================================================

df = pd.read_csv(uploaded_file)

df["Datetime"] = pd.to_datetime(df["Datetime"])

# NET MW only
df = df[df["Attribute"] == "NET MW"].copy()

# Helper columns
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

# =====================================================
# MONTH FILTER
# =====================================================

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
# TOTAL DEMAND TOGGLE
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
    filtered[filtered["Plant"] == "TOTAL DEMAND"]
    .groupby("Datetime", as_index=False)["Value"]
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
# DRAG & DROP STACK ORDER
# =====================================================

st.sidebar.subheader("Drag Plant Order")

plant_order = sort_items(
    items=plant_order,
    direction="vertical"
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
# CHART
# =====================================================

fig = go.Figure()

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

# =====================================================
# TOTAL DEMAND LINE
# =====================================================

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

# =====================================================
# FORMAT
# =====================================================

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

# =====================================================
# DISPLAY
# =====================================================

st.plotly_chart(
    fig,
    use_container_width=True
)
