import os
from .dependencies import get_current_user, get_current_magic, get_session
from .models import User
from typing import AsyncGenerator
from sqlmodel import Session
from fastapi import HTTPException, Depends
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from langchain.tools import BaseTool
from langchain_ollama import ChatOllama
from .llm_tools import create_tools, get_system_prompt 
from dotenv import load_dotenv
load_dotenv()

LLM_MODEL = os.environ["LLM_MODEL"]
LLM_API_URL = os.environ["LLM_API_URL"]

model = ChatOllama(
    base_url=LLM_API_URL,
    model=LLM_MODEL,
    validate_model_on_init=True
)

async def chat(
    messages : list[dict],
    user : User,
    magic : str,
    session : Session
) -> list[BaseMessage]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
    
    Returns:
        list[BaseMessage]: The LLM response messages.
    """
    
    tools : list[BaseTool] = create_tools(user=user, magic=magic, session=session)

    agent = create_agent(
        model=model,
        system_prompt=get_system_prompt(user=user, magic=magic, session=session),
        tools=tools
    )

    try:
# pyright: reportArgumentType=false 
        response = await agent.ainvoke({"messages": messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM response.\nDetail: {str(e)}")
    
    try:
        response_messages : list[BaseMessage] = response["messages"]
        response_text = str(response_messages[-1].content)
    except:
        raise HTTPException(status_code=500, detail=f"LLM message not found in response.\nLLM response: {response}")
    
    return response_messages

async def chat_stream(
    messages : list[dict],
    user : User,
    magic : str,
    session : Session
) -> AsyncGenerator[str, None]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
    
    Yields:
        str: The next chunk of the LLM response.
    """
    
    tools : list[BaseTool] = create_tools(user=user, magic=magic, session=session)

    agent = create_agent(
        model=model,
        system_prompt="",#get_system_prompt(user=user, magic=magic, session=session),
        tools=[]#tools
    )

    async for token, metadata in agent.astream(
        {"messages":messages},
        stream_mode="messages"
    ):
        node = metadata["langgraph_node"]
        content : list[dict] = token.content_blocks

        if node != "model": break
        if not content: break
        if not content.get("text"): break
        yield str(content["text"])
        # content = token.content_blocks
        # for step, data in chunk.items():
        #     content = data["messages"][-1].content_blocks
        #     yield content
        #     print(f"step : {step}")
        #     print(f"content : {content}")
