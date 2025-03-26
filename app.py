import streamlit as st

pages = {
    "Navigation": [
        st.Page("src/chatbot.py", title="Chatbot"),
        st.Page("src/show.py", title="Show Users, Customers, and Offices"),
        st.Page("src/org_chart.py", title="Organizational Chart creation"),
    ]

}

pg = st.navigation(pages)
pg.run()