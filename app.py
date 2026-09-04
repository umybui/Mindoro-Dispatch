import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
    st.stop()

# =====================================================
# LOAD DATA
# =====================================================

df = pd.read_csv(uploaded_file)

df["Datetime"] = pd.to_datetime(df["Datetime"])

df = df[df["Attribute"] == "NET MW"].copy()

df["Month"] = df["Datetime"].dt.month
df["Day"] = df["Datetime"].dt.day

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("Filters")

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

available_days = sorted(df["Day"].unique())

selected_days = st.sidebar.multiselect(
    "Day of Month",
    options=available_days,
    default=available_days
)

sort_option = st.sidebar.selectbox(
    "Plant Order",
    [
        "Alphabetical",
        "Largest Generator First",
        "Smallest Generator First"
    ]
)

show_demand = st.sidebar.checkbox(
    "Show Total Demand",
    value=True
)

# =====================================================
# APPLY FILTERS
# =====================================================

filtered = df[
    (df["Month"].isin(selected_months)) &
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
# GENERATORS
# =====================================================

generation = filtered[
    ~filtered["Plant"].isin([
        "TOTAL DEMAND",
        "TOTAL GENERATION DISPATCH",
        "SYNCHRO  \nEXPORT (-)  \nIMPORT (+)"
    ])
]

# =====================================================
# SORT ORDER
# =====================================================

plant_stats = (
    generation
    .groupby("Plant")["Value"]
    .mean()
    .reset_index()
)

if sort_
