from fastapi import FastAPI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.checkpoint.memory import MemorySaver
from src.functions_models import detect_intent, router, general_chat
from src.addition_workflow import read_file, interpret, add
from src.deletion_workflow import delete
from pydantic import BaseModel
from typing import Union, Optional
import logging

# Configure logging
logging.basicConfig(
    filename="chat_output.log",  # Log file name
    level=logging.INFO,          # Log level
    format="%(asctime)s - %(levelname)s - %(message)s"  # Log format
)

app = FastAPI()

class GraphState(MessagesState):
    """
    Graph state is a dictionary that contains information we want to propagate to, and modify in, each graph node.
    """
    intent: str
    file_path: Optional[str]
    file_content: Optional[Union[dict, list, str]]
    raw_input: Optional[str]
    output_schema: Optional[str]
    result_json: Optional[dict]
    delete_attribute: Optional[str] = None
    delete_value: Optional[Union[str, int, list[int, str]]] = None

graph = StateGraph(GraphState)

graph.add_node("detect_intent", detect_intent)
graph.add_node("read_file", read_file)
graph.add_node("interpret", interpret)
graph.add_node("add", add)
graph.add_node("delete", delete)
graph.add_node("general_chat", general_chat)

graph.add_edge(START, "detect_intent")
graph.add_conditional_edges("detect_intent", router)
graph.add_edge("read_file", "interpret")
graph.add_edge("interpret", "add")
graph.add_edge("add", END)
graph.add_edge("delete", END)
graph.add_edge("general_chat", END)

checkpointer = MemorySaver()
workflow = graph.compile(checkpointer=checkpointer)

class ChatInput(BaseModel):
    input_text: str
    file_path: Optional[str] = None

@app.post("/chat/")
async def chat(chat_input: ChatInput):
    chat_text = chat_input.input_text
    config = {"configurable": {"thread_id": "api"}}
    if chat_input.file_path is not None:
        output = workflow.invoke({
            'messages': HumanMessage(content=chat_text),
            'file_path': chat_input.file_path
            }, config)
    else: output = workflow.invoke({'messages': HumanMessage(content=chat_text)}, config)
    logging.info(f"Workflow Output: {output}")
    ai_message = output['messages'][-1].content
    return ai_message
