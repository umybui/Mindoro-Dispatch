import streamlit as st

st.set_page_config(
    page_title="Island Dispatch Dashboard",
    layout="wide"
)

st.title("Philippine Island Dispatch Dashboard")

st.markdown("---")

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
    }
]

cols = st.columns(len(areas))

for col, area in zip(cols, areas):

    with col:

        st.image(
            area["image"],
            use_container_width=True
        )

        if st.button(
            area["name"],
            use_container_width=True
        ):
            st.switch_page(
                area["page"]
            )
