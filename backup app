import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Mindoro Dispatch Dashboard",
    layout="wide"
)

st.title("Mindoro Dispatch Dashboard")

uploaded_file = st.file_uploader(
    "Upload mindoro dispatch.csv",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Please upload mindoro dispatch.csv")
    st.stop()

# Read CSV
df = pd.read_csv(uploaded_file)

# Datetime conversion
df["Datetime"] = pd.to_datetime(df["Datetime"])

# Keep NET MW only
df = df[df["Attribute"] == "NET MW"]

# Combined Total Demand
total_demand = (
    df[df["Plant"] == "TOTAL DEMAND"]
    .groupby("Datetime", as_index=False)["Value"]
    .sum()
)

# Generation plants only
generation = df[
    ~df["Plant"].isin([
        "TOTAL DEMAND",
        "TOTAL GENERATION DISPATCH",
        "SYNCHRO  \nEXPORT (-)  \nIMPORT (+)"
    ])
]

fig = go.Figure()

# Stacked Areas
for plant in sorted(generation["Plant"].unique()):

    temp = generation[generation["Plant"] == plant]

    fig.add_trace(
        go.Scatter(
            x=temp["Datetime"],
            y=temp["Value"],
            name=plant,
            mode="lines",
            stackgroup="generation"
        )
    )

# Total Demand Line
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

fig.update_layout(
    title="Mindoro Dispatch (NET MW)",
    hovermode="x unified",
    height=800,
    xaxis_title="Datetime",
    yaxis_title="MW",
    legend_title="Plant"
)

# Slider
fig.update_xaxes(
    rangeslider_visible=True
)

st.plotly_chart(
    fig,
    use_container_width=True
)
