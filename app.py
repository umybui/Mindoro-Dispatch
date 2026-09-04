import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Mindoro Dispatch", layout="wide")

st.title("Mindoro Dispatch Dashboard")

df = pd.read_csv("mindoro dispatch.csv")

df["Datetime"] = pd.to_datetime(df["Datetime"])

df = df[df["Attribute"] == "NET MW"]

total_demand = (
    df[df["Plant"] == "TOTAL DEMAND"]
    .groupby("Datetime", as_index=False)["Value"]
    .sum()
)

generation = df[
    ~df["Plant"].isin([
        "TOTAL DEMAND",
        "TOTAL GENERATION DISPATCH",
        "SYNCHRO  \nEXPORT (-)  \nIMPORT (+)"
    ])
]

fig = go.Figure()

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

fig.add_trace(
    go.Scatter(
        x=total_demand["Datetime"],
        y=total_demand["Value"],
        name="TOTAL DEMAND",
        mode="lines",
        line=dict(color="black", width=4)
    )
)

fig.update_layout(
    title="Mindoro Dispatch (NET MW)",
    hovermode="x unified",
    height=800
)

fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig, use_container_width=True)
