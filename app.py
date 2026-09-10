import streamlit as st

st.set_page_config(
    page_title="Island Dispatch Dashboard",
    layout="wide"
)

st.title("Philippine Island Dispatch Dashboard")

areas = [
    {
        "name": "Mainland Mindoro",
        "page": "pages/01_Mainland_Mindoro.py",
        "image": "Mainland Mindoro.png"
    },
    {
        "name": "Mainland Palawan",
        "page": "pages/02_Mainland_Palawan.py",
        "image": "Mainland Palawan.png"
    },
    {
        "name": "Mainland Marinduque",
        "page": "#",
        "image": "Mainland Marinduque.png"
    },
    {
        "name": "Mainland Masbate",
        "page": "#",
        "image": "Mainland Masbate.png"
    },
    {
        "name": "Mainland Catanduanes",
        "page": "#",
        "image": "Mainland Catanduanes.png"
    }
]

st.markdown("""
<style>

[data-testid="stImage"] img{
    height:320px !important;
    object-fit:contain !important;
    border-radius:16px;
}

.island-title{
    text-align:center;
    font-weight:700;
    font-size:22px;
    margin-top:10px;
    margin-bottom:10px;
}

div[data-testid="stHorizontalBlock"] > div {
    min-width: 340px !important;
}

</style>
""", unsafe_allow_html=True)
