import streamlit as st

pages = {
    "Navigation": [
        st.Page("chatbot.py", title="Chatbot"),
        st.Page("show.py", title="Show Users, Customers, and Offices"),
        st.Page("org_chart.py", title="Organizational Chart creation"),
    ]

}

pg = st.navigation(pages)
pg.run()