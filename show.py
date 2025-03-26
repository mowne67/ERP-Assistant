import streamlit as st
import pandas as pd
import json

def load_json_data(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        st.error(f"Error decoding JSON file: {file_path}")
        return None

def show_data():
    """Display users, customers, and offices as tables."""
    st.header("Users, Customers, and Offices")

    # Paths to JSON files
    users_file = "users.json"
    customers_file = "customers.json"
    offices_file = "offices.json"

    # Load and display data
    users_data = load_json_data(users_file)
    customers_data = load_json_data(customers_file)
    offices_data = load_json_data(offices_file)

    if users_data:
        with st.expander("Users"):
            st.table(pd.DataFrame(users_data))  # Convert JSON list to DataFrame and display as table

    if customers_data:
        with st.expander("Customers"):
            st.table(pd.DataFrame(customers_data))  # Convert JSON list to DataFrame and display as table

    if offices_data:
        with st.expander("Offices"):
            st.table(pd.DataFrame(offices_data)) 

show_data()