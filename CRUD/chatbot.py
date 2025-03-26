import streamlit as st
import time
import requests
import os

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
    st.session_state['chat_history'] = []
    try:
        # Send "Hi" to the API
        response = requests.post("http://127.0.0.1:8000/chat/", json={"input_text": "Hi"})
        output = response.json()
        # Add the bot's response to the chat history
        st.session_state['chat_history'].append({'bot': output})
    except:
        st.session_state['chat_history'].append({'bot': "There seems to be a problem. Please try again."})

if user_input:
    instance = {'user':user_input}
    if uploaded_file:
        try:
            response = requests.post("http://127.0.0.1:8000/chat/", json= {"input_text": user_input, "file_path": file_path})
            output = response.json()
        except: output = "There seems to be a problem. Please try again."    
    else: 
        try:
            response = requests.post("http://127.0.0.1:8000/chat/", json= {"input_text": user_input})
            output = response.json()
        except: output = "There seems to be a problem. Please try again."
       
    
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

