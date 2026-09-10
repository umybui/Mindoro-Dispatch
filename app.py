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
        "name": "Marinduque",
        "page": "#",
        "image": "Mainland Mindoro.png"
    },
    {
        "name": "Romblon",
        "page": "#",
        "image": "Mainland Palawan.png"
    },
    {
        "name": "Busuanga",
        "page": "#",
        "image": "Mainland Mindoro.png"
    }
]

st.markdown("""
<style>

[data-testid="stImage"] img{
    height:250px !important;
    object-fit:contain !important;
    border-radius:12px;
}

.island-title{
    text-align:center;
    font-weight:bold;
    font-size:20px;
    margin-top:10px;
    margin-bottom:10px;
}

</style>
""", unsafe_allow_html=True)

# Scrollable horizontal gallery
gallery = st.container(horizontal=True)

with gallery:

    cols = st.columns(len(areas))

    for col, area in zip(cols, areas):

        with col:

            st.image(
                area["image"],
                use_container_width=True
            )

            st.markdown(
                f"<div class='island-title'>{area['name']}</div>",
                unsafe_allow_html=True
            )

            if area["page"] != "#":

                if st.button(
                    f"Open",
                    key=area["name"],
                    use_container_width=True
                ):
                    st.switch_page(area["page"])

            else:

                st.button(
                    "Coming Soon",
                    key=f"soon_{area['name']}",
                    disabled=True,
                    use_container_width=True
                )
