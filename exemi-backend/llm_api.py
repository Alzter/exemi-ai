import os
from .dependencies import get_current_user, get_current_magic, get_session
from .models import User
from typing import AsyncGenerator, Callable, Any
from sqlmodel import Session
from fastapi import HTTPException, Depends, BackgroundTasks
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
    validate_model_on_init=True,
    streaming=True
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
    background_tasks : BackgroundTasks,
    user : User,
    magic : str,
    session : Session,
    end_function : Callable | None = None,
    end_function_kwargs : dict[str, Any] | None = None,
    include_tool_responses : bool = True
) -> AsyncGenerator[str, None]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).

    Allows for the calling of an arbitrary function after the LLM stream
    is complete using FastAPI's background tasks feature. This is used
    for saving the LLM's response to the DB once streaming is complete.

    For more information, see "What is correct way to do DB operation after successfully streaming response?":
    https://github.com/fastapi/fastapi/discussions/11433#discussioncomment-9161859

    Also see LangChain Agent LLM Token streaming:
    https://docs.langchain.com/oss/python/langchain/streaming/overview#llm-tokens
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
        end_function (Callable | None, optional): Arbitrary function to execute after the LLM response is complete. Defaults to None.
        end_function_kwargs (dict[str, Any], optional):
            Keyword arguments to use when calling end_function. Defaults to None.
            NOTE: A keyword argument "messages" (list[dict[str,str]]) is automatically added containing the LLM's response and any tool calls in OpenAI chat template format.
        include_tool_responses (bool, optional): Includes the LLM's tool call responses in the streamed response. The reponse is not included in the database.
    
    Yields:
        str: The next chunk of the LLM response.
    """
    
    tools : list[BaseTool] = create_tools(user=user, magic=magic, session=session)

    agent = create_agent(
        model=model,
        system_prompt=get_system_prompt(user=user, magic=magic, session=session),
        tools=tools
    )
    
    # We will store the tool and LLM responses in
    # a separate list using OpenAI format.
    response_messages : list[dict[str,str]] = []

    # We will store the LLM's streamed response
    # chunks in a list. Once generation is complete,
    # we will concatenate all the chunks to get the
    # completed message.
    chunks : list[str] = []

    if end_function_kwargs is None: end_function_kwargs = {}

    try:

        async for token, metadata in agent.astream(
            {"messages":messages},
            stream_mode="messages"
        ):
            node = metadata["langgraph_node"]
            content : list[dict] = token.content_blocks

            if not content: continue # Ignore empty chunks

            # No idea why LangChain wraps LLM tokens in a list.
            content : dict = content[-1]
            
            chunk : str | None = None
            
            if not content.get("type"): continue

            match content["type"]:

                # When the LLM executes a tool call,
                # yield the text "I am calling the function: <tool name>"
                case "tool_call_chunk":

                    # Obtain the function name of the LLM's tool call
                    # (e.g., "get_assignments")
                    tool_name : str | None = content.get("name")

                    if tool_name:
                        # Make the tool name human readable
                        # "get_assignments_from_Canvas" -> "get assignments from Canvas"
                        tool_name = tool_name.replace("_", " ")

                        # Add the chunk: "I am calling the function: <tool name>"
                        chunk = f"\n\nI am calling the function: **{tool_name}**. Please wait...\n\n"

                        # Consider the LLM calling a tool as its own message.
                        response_messages.append({"role":"assistant", "content":chunk.strip()})

                case "text":
                    chunk = content.get("text")
                    if not chunk: continue

                    if node == "tools":
                        if include_tool_responses:
                            chunk = f"\n\nI have obtained the following information:\n\n---\n\n{chunk}\n\n---\n\n**Please wait while I reason with this information...**\n\n"
                        
                        # Add the tool call into the list of messages.
                        response_messages.append({"role":"tool", "content":chunk})

                    elif node == "model":
                        # Only include LLM text in the final message.
                        chunks.append(chunk)

            if chunk is not None:
                yield chunk
    
    finally:
        # Add the LLM response to the DB even if an exception is encountered

        if end_function is not None:
            response_text = "".join(chunks).strip()

            if response_text:
                response_messages.append({"role":"assistant", "content":response_text})

            end_function_kwargs["messages"] = response_messages

            background_tasks.add_task(end_function, **end_function_kwargs)
