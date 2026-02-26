import os
from .dependencies import get_current_user, get_current_magic, get_session
from .models import User
from typing import AsyncGenerator, Callable, Any
from sqlmodel import Session
from fastapi import HTTPException, Depends, BackgroundTasks
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, convert_to_openai_messages
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
) -> list[dict[str, Any]]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
    
    Returns:
        list[dict[str, Any]]: The LLM response messages in OpenAI format.
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
        response_messages_openai : list[dict[str, Any]] = convert_to_openai_messages(response_messages)
        #response_text = str(response_messages[-1].content)
    except:
        raise HTTPException(status_code=500, detail=f"LLM message not found in response.\nLLM response: {response}")
    
    return response_messages_openai

async def chat_stream(
    messages : list[dict],
    background_tasks : BackgroundTasks,
    user : User,
    magic : str,
    session : Session,
    end_function : Callable | None = None,
    end_function_kwargs : dict[str, Any] | None = None,
    include_tool_responses : bool = False
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
    tools = create_tools(user=user, magic=magic, session=session)

    agent = create_agent(
        model=model,
        system_prompt=get_system_prompt(user=user, magic=magic, session=session),
        tools=tools,
    )

    if end_function_kwargs is None:
        end_function_kwargs = {}

    response_messages: list[dict] = []
    assistant_chunks: list[str] = []

    # Track current tool calls
    tool_calls: dict[str, dict] = {}
    tool_results: list[dict] = []
    last_tool_id: str | None = None
    last_tool_name: str | None = None

    try:
        async for token, metadata in agent.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            node = metadata["langgraph_node"]
            blocks = token.content_blocks
            if not blocks:
                continue

            content = blocks[-1]
            t = content.get("type")
            if not t:
                continue

            chunk: str | None = None

            # ----------------------------------
            # TOOL CALL START / ARGUMENTS
            # ----------------------------------
            if t == "tool_call_chunk":
                tool_id = content.get("id")
                tool_name = content.get("name")

                if tool_id and tool_name:
                    last_tool_id = tool_id
                    last_tool_name = tool_name

                    if tool_id not in tool_calls:
                        tool_calls[tool_id] = {
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": "{}",
                            },
                        }

                    readable = tool_name.replace("_", " ")
                    chunk = f"\n\nI am calling the function **{readable}**. Please wait...\n\n"

            elif t == "tool_call_arguments":
                tool_id = content.get("id")
                args = content.get("arguments", "")
                if tool_id in tool_calls:
                    tool_calls[tool_id]["function"]["arguments"] += args

            # ----------------------------------
            # TEXT OUTPUT
            # ----------------------------------
            elif t == "text":
                text = content.get("text")
                if not text:
                    continue

                if node == "tools":
                    # TOOL RESULT
                    if last_tool_id:
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": last_tool_id,
                            "name": last_tool_name,
                            "content": text,
                        })

                    if include_tool_responses:
                        chunk = (
                            "\n\n--- Tool Result ---\n"
                            f"{text}\n"
                            "-------------------\n\n"
                        )

                elif node == "model":
                    assistant_chunks.append(text)
                    chunk = text

            if chunk:
                yield chunk

        # ----------------------------------
        # FINALIZE OPENAI MESSAGE HISTORY
        # ----------------------------------

        # 1. Assistant tool calls
        if tool_calls:
            response_messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": list(tool_calls.values()),
            })

        # 2. Tool results
        response_messages.extend(tool_results)

        # 3. Final assistant text
        assistant_text = "".join(assistant_chunks).strip()
        if assistant_text:
            response_messages.append({
                "role": "assistant",
                "content": assistant_text,
            })

    finally:
        if end_function:
            end_function_kwargs["messages"] = response_messages
            background_tasks.add_task(end_function, **end_function_kwargs)
