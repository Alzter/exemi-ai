import os
import json
from datetime import datetime
from pydantic import BaseModel
from .dependencies import get_current_user, get_current_magic, get_session
from .models import User, TaskList, TaskAutofillCreate, TaskAutofillResponse, TaskCreate
from typing import AsyncGenerator, Callable, Any
from sqlmodel import Session
from fastapi import HTTPException, Depends, BackgroundTasks
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, AIMessage
from langchain.tools import BaseTool
from langchain_ollama import ChatOllama
from .llm_tools import create_tools
from .routers.llm_prompt import get_system_prompt, get_summarising_prompt, get_update_user_bio_prompt, prepare_task_generation, get_task_autofill_prompt_for_user
from dotenv import load_dotenv
import warnings
load_dotenv()


class CreateTasksForUserResult(BaseModel):
    tasks: TaskList
    llm_bypassed: bool = False


LLM_MODEL = os.environ["LLM_MODEL"]
LLM_API_URL = os.environ["LLM_API_URL"]

model = None
try:
    model = ChatOllama(
        base_url=LLM_API_URL,
        model=LLM_MODEL,
        validate_model_on_init=True,
        # streaming=True
    )
except:
    warnings.warn("Ollama server unreachable: AI functionality will not work")

async def update_user_bio(
    new_information : str,
    previous_biography : str | None,
    max_words : int = 300
) -> str:
    """
    Update the user's biography string to contain new information.

    Args:
        new_information (str): The new information to include in the biography string.
        previous_biography (str | None): The user's past biography, if exists.
        max_words (int, optional): Biography word limit. Defaults to 300.
    
    Returns:
        str: The updated biography text.
    """
    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")
    
    prompt = get_update_user_bio_prompt(
        max_words=max_words,
        existing_information=previous_biography
    )
    
    messages = [{"role":"system", "content":prompt}, {"role":"user","content":new_information}]

    response : AIMessage = model.invoke(messages)
    return str(response.content)

async def summarise(
    chat_message_log : list[dict],
    max_words : int = 200
) -> str:
    """
    Summarise a conversation between
    the user and the chatbot.

    Args:
        chat_message_log (list[dict]): List of messages to summarise.
        max_words (int): Conversation summary word limit. Defaults to 200.

    Raises:
        HTTPException: If the LLM is offline, raises a 500.

    Returns:
        str: The conversation summary.
    """
    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")

    # Parse conversation message dict into a string
    messages_text = json.dumps(chat_message_log, ensure_ascii=False).encode("utf-8")

    messages = [
        {"role":"system", "content":get_summarising_prompt(
            max_words=max_words
        )},
        {"role":"user", "content": messages_text}
    ]

    response : AIMessage = model.invoke(messages)
    return str(response.content)

async def create_tasks_for_user(
    username : str,
    user : User,
    session : Session
) -> CreateTasksForUserResult:
    prep = prepare_task_generation(
        username=username,
        requesting_user=user,
        session=session,
    )
    if prep.bypass_llm:
        assert prep.task_list_if_bypass is not None
        return CreateTasksForUserResult(tasks=prep.task_list_if_bypass, llm_bypassed=True)

    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")

    messages = [{"role":"system", "content":prep.prompt}]

    model_structured = model.with_structured_output(TaskList)

    tasks = model_structured.invoke(messages)

    return CreateTasksForUserResult(tasks=tasks, llm_bypassed=False)

async def autofill_task_for_user(
    task : TaskAutofillCreate,
    username : str,
    user : User,
    session : Session
) -> TaskCreate:
    """
    Given a task name, get the LLM
    to generate fields for its assignment
    ID, due date, and duration in minutes.
    """

    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")
    
    prompt = get_task_autofill_prompt_for_user(
        task=task,
        username=username,
        user=user,
        session=session
    )

    messages = [{"role":"system", "content": prompt}]
    model_structured = model.with_structured_output(TaskAutofillResponse)
    task_fields : TaskAutofillResponse = model_structured.invoke(messages)

    task_create = TaskCreate(
        name=task.name,
        description=task_fields.description,
        assignment_id=task_fields.assignment_id,
        duration_mins=task_fields.duration_mins,
        due_at=task.due_at
    )

    return task_create

async def chat(
    messages : list[dict],
    user : User,
    magic : str,
    session : Session,
    system_prompt : str | None = None,
    unit_id : int | None = None
) -> list[BaseMessage]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
        system_prompt (str):
            System prompt to use for the model.
            If not given, uses the user's system prompt (routers/llm_prompt.get_system_prompt).
            Defaults to None.
        unit_id (int | None, optional): Which unit to focus on. If not given, provides information for all units. Defaults to None.

    Raises:
        HTTPException: If the LLM is offline, raises a 500.
    
    Returns:
        list[BaseMessage]: The LLM response messages.
    """

    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")

    if not system_prompt:
        system_prompt = await get_system_prompt(user=user, session=session, unit_id=unit_id)

    tools : list[BaseTool] = create_tools(user=user, session=session)

    agent = create_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools
    )

    try:
# pyright: reportArgumentType=false 
        response = await agent.ainvoke({"messages": messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM response.\nDetail: {str(e)}")
    
    try:
        response_messages : list[BaseMessage] = response["messages"]
        # response_text = str(response_messages[-1].content)
    except:
        raise HTTPException(status_code=500, detail=f"LLM message not found in response.\nLLM response: {response}")
    
    return response_messages

async def chat_stream(
    messages : list[dict],
    background_tasks : BackgroundTasks,
    user : User,
    magic : str,
    session : Session,
    system_prompt : str | None = None,
    unit_id : int | None = None,
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
        system_prompt (str):
            System prompt to use for the model.
            If not given, uses the user's system prompt (routers/llm_prompt.get_system_prompt).
            Defaults to None.
        unit_id (int | None, optional): Which unit to focus on. If not given, provides information for all units. Defaults to None.
        end_function (Callable | None, optional): Arbitrary function to execute after the LLM response is complete. Defaults to None.
        end_function_kwargs (dict[str, Any], optional):
            Keyword arguments to use when calling end_function. Defaults to None.
            NOTE: A keyword argument "messages" (list[dict[str,str]]) is automatically added containing the LLM's response and any tool calls in OpenAI chat template format.
        include_tool_responses (bool, optional): Includes the LLM's tool call responses in the streamed response. The reponse is not included in the database.
    
    Raises:
        HTTPException: If the LLM is offline, raises a 500.

    Yields:
        str: The next chunk of the LLM response.
    """
    
    if not model: raise HTTPException(status_code=500, detail="Error reaching LLM: Ollama server offline")

    if not system_prompt:
        system_prompt = await get_system_prompt(user=user, session=session, unit_id=unit_id)

    tools : list[BaseTool] = create_tools(user=user, session=session)

    agent = create_agent(
        model=model,
        system_prompt=system_prompt,
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
    
    last_tool_name : str | None = None

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
                        last_tool_name = tool_name
                        # Make the tool name human readable
                        # "get_assignments_from_Canvas" -> "get assignments from Canvas"
                        tool_name = tool_name.replace("_", " ")

                        # Add the chunk: "I am calling the function: <tool name>"
                        # chunk = f"\n\nI am calling the function: **{tool_name}**. Please wait...\n\n"

                        # Consider the LLM calling a tool as its own message.
                        # response_messages.append({"role":"assistant", "content":chunk.strip()})

                case "text":
                    chunk = content.get("text")
                    if not chunk: continue

                    if node == "tools":
                        system_prompt_amendment = ""
                        if last_tool_name: system_prompt_amendment += f"Obtained result from tool call: {last_tool_name}\n\n"
                        system_prompt_amendment += f"Use the following information to inform your response:\n\n{chunk}"

                        # Add the tool call into the list of messages.
                        # response_messages.append({"role":"system", "content":system_prompt_amendment})

                        if include_tool_responses:
                            chunk = f"\n\nI have obtained the following information:\n\n---\n\n{chunk}\n\n---\n\n**Please wait while I reason with this information...**\n\n"
                        else:
                            chunk = None

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
