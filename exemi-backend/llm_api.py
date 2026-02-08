import os
from fastapi import HTTPException
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from .llm_tools import SYSTEM_PROMPT, TOOLS 
from dotenv import load_dotenv
load_dotenv()

LLM_MODEL = os.environ["LLM_MODEL"]
LLM_API_URL = os.environ["LLM_API_URL"]

model = ChatOllama(
    base_url=LLM_API_URL,
    model=LLM_MODEL,
    validate_model_on_init=True
)

agent = create_agent(
    model=model,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT
)

async def chat(
    messages : list[dict]
):
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
    
    Returns:
        str: The LLM's response.
    """

# pyright: reportArgumentType=false 
    response = await agent.ainvoke({"messages": messages})

    try:
        response_messages : list[BaseMessage] = response["messages"]
        response_text = response_messages[-1].content
    except:
        raise HTTPException(status_code=500, detail=f"LLM did not generate response for message.\nLLM output: {response}")
    
    return response_text
