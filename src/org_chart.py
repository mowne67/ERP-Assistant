from __future__ import annotations
import streamlit as st
from typing import Optional, List
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import json
import networkx as nx
import plotly.graph_objects as go

# Load environment variables
load_dotenv()

# Define Employee and EmployeeList models
class Employee(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    position: Optional[str]
    reportees: Optional[List[str]] = []

class EmployeeList(BaseModel):
    employees: List[Employee]

EmployeeList.model_rebuild()

def extract_structure(transcription: str) -> EmployeeList:
    """
    Extracts the organizational structure from the transcription using Google Generative AI with structured output.
    """
    prompt = f"""
    Extract the organizational structure from the following transcription and return it in the specified structure.
    Transcription:
    {transcription}
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not configured in Streamlit secrets.")
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.0)
    response = llm.with_structured_output(EmployeeList).invoke(prompt)

    return response

def get_node_depth(G, node_id):
    """
    Recursively finds the depth of a node in a directed graph.
    """
    if G.in_degree(node_id) == 0:  # No parent nodes
        return 0
    else:
        return 1 + max(get_node_depth(G, parent) for parent in G.predecessors(node_id))

def create_org_chart(org_structure: dict):
    """
    Creates an organizational chart using NetworkX and Plotly with a strict hierarchical layout.
    """
    G = nx.DiGraph()

    # Add nodes and edges
    for employee in org_structure['employees']:
        G.add_node(employee['id'], label=employee['name'], position=employee.get('position', 'Unknown'))
        for reportee_id in employee.get('reportees', []):
            G.add_edge(employee['id'], reportee_id)

    # Calculate depth for each node
    for node in G.nodes:
        G.nodes[node]['layer'] = get_node_depth(G, node)

    # Generate a strict hierarchical layout
    pos = nx.multipartite_layout(G, subset_key="layer")

    # Extract edges
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')

    # Extract nodes
    node_x, node_y, node_text = [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{G.nodes[node]['label']} ({G.nodes[node]['position']})")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition='top center',
        marker=dict(size=10, color='lightblue', line=dict(width=2))
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False, hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=0),
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False)
                    ))

    return fig

# Streamlit app
st.set_page_config(page_title="Organizational Chart", page_icon="📊", layout="wide")
st.title("Organizational Chart Generator")

# File uploader for the transcription file
file = st.file_uploader("Upload the transcription file", type=['txt'])
if file:
    # Read the transcription
    transcription = file.getvalue().decode("utf-8")

    # Extract the organizational structure
    try:
        org_structure = extract_structure(transcription)
        org_structure_json = org_structure.model_dump_json(indent=4)
        org_structure_dict = json.loads(org_structure_json)

        # Display extracted structure
        st.json(org_structure_dict)

        # Create and display the organizational chart
        st.subheader("Organizational Chart")
        fig = create_org_chart(org_structure_dict)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred during extraction or visualization: {str(e)}")
