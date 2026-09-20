from langchain_anthropic import ChatAnthropic  # For ChatAnthropic
from pydantic import BaseModel, Field
from typing import List, Annotated, Optional, Union, Literal
from langchain_core.messages import SystemMessage
import json

import os
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

@lru_cache
def get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured in Streamlit secrets.")
    return ChatAnthropic(model="claude-sonnet-4-6", temperature=0.0, api_key=api_key)

class User(BaseModel):
    id: int = Field(..., description="Unique  ID")
    username: str = Field(..., description="Generated username")
    email: str = Field(..., description="User's email")
    designation: str = Field(..., description="User's designation in the company")
    department: str = Field(..., description="Department name")
    phone: str = Field(..., description="User phone details")

class Address(BaseModel):
    address1: str
    address2: Optional[str]
    city: str
    state: str
    zip: str
    country: Optional[str]
    county: Optional[str]

class Customer(BaseModel):
    id: int
    name: str
    address: Address

class Office(BaseModel):
    id: int
    location: str
    size: int

class IntentEntityPath(BaseModel):
    intent: Literal["add", "delete", "general"] = Field(description="The classified intent: The input must specify something to add or delete in order to have intent as add or delete, everything else is general chat.")
    entity: Literal["user", "customer", 'office', 'N/A'] = Field(description="The classified entity. Applicable only when the intent is add or delete.")
    #addition_file_path: str = None
    delete_attribute: Optional[str] = Field(description="Attribute to delete. Applicable only when the intent is delete.")
    delete_value: Optional[Union[str, int, list[int, str]]] = Field(description="Value to delete. Applicable only when the intent is delete.")

def detect_intent(state):
    "This node will detect intent"

    chat_input = state['messages'][-1].content
    response = get_llm().with_structured_output(IntentEntityPath).invoke(chat_input)

    return {
        #'file_path': response.addition_file_path, 
        'output_schema': response.entity, 
        'intent': response.intent,
        'delete_attribute': response.delete_attribute,
        'delete_value': response.delete_value}

def router(state) -> Literal['read_file', 'delete', 'general_chat']:
    if state['intent'] == 'add':
        return 'read_file'
    if state['intent'] == 'delete':
        return 'delete'
    if state['intent'] == 'general':
        return 'general_chat'

def general_chat(state):
    messages_state = state['messages']
    prompt = """
    You are an assitant. You can add, delete users, customers and offices in the database. 
    If they ask for help, give examples like 'Add a new user from the file.' after uploading the file or 'Delete user with username: john_doe.'. 
    Acceptable file formats are: csv, xlsx, pdf, txt, json.
    Suggest the user that they must upload a file in order to add new users/customers/offices. Addition cannot be done manually, a file must be uploaded.
    If the user deviates from the tasks at hand, direct them back to our context.
    If the user asks for exmaple schemas, provide them with the following:
    1. User: user_id, username, email, designation, department, phone
    2. Customer: customer_id, name, address (address1, address2, city, state, zip, country, county)
    3. Office: office_id, location, size
    \n
    Do not ask questions unless you're suggesting them to ask about schemas. Always be assertive in your reponses and guide the user. 
    Always circle back to what the user wants to do in terms of adding or deleting entities.
    """
    system_message = SystemMessage(content=prompt)
    response = get_llm().invoke([system_message] + messages_state)
    return {'messages': response}
