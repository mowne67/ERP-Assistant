import streamlit as st
import time
import os
import uuid

from langchain_core.messages import HumanMessage
from src.backend import workflow

st.set_page_config(page_title="CRUD Chatbot", page_icon="🤖", layout="wide")
st.title("CRUD Assistant")

with st.sidebar:

    uploaded_file = st.file_uploader("Upload the necessary file for addition", type = ['csv', 'xlsx', 'pdf', 'txt', 'json'])
    
    if uploaded_file:
        # Create input_bucket directory if it doesn't exist
        os.makedirs("input_bucket", exist_ok=True)
        
        # Save the file
        file_path = os.path.join("input_bucket", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
            
        st.success(f"File saved successfully at {file_path}")

user_input = st.chat_input("")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [{
        'bot': "Hi! Upload a file to add ERP records, or ask me to delete or explain data."
    }]
    st.session_state['thread_id'] = str(uuid.uuid4())

if user_input:
    instance = {'user':user_input}
    try:
        state = {'messages': HumanMessage(content=user_input)}
        if uploaded_file:
            state['file_path'] = file_path
        output = workflow.invoke(
            state,
            {"configurable": {"thread_id": st.session_state['thread_id']}},
        )['messages'][-1].content
    except Exception as error:
        output = f"There seems to be a problem: {error}"
       
    
    instance['bot'] = output
    st.session_state['chat_history'].append(instance)

for index, chat in enumerate(st.session_state['chat_history']):
    latest = index == len(st.session_state.chat_history) - 1
    if 'user' in chat:
        with st.chat_message('user'):
            st.write(chat['user'], unsafe_allow_html=True)
    if 'bot' in chat:
        with st.chat_message('ai'):
            if latest:
                def stream_data():
                    for word in chat['bot'].split(" "):
                        yield word + " "
                        time.sleep(0.02)
                st.write_stream(stream_data)
            else:
                st.write(chat['bot'])
