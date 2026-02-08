import os
import json
import inspect
from typing import get_type_hints, Callable, Any
from fastapi import Depends, HTTPException, Query
import litellm
from litellm import completion
from litellm.types.utils import Message
import instructor
from pydantic import BaseModel
from llm_tools import SYSTEM_PROMPT, TOOLS 
from dotenv import load_dotenv
load_dotenv()

LLM_MODEL = os.environ["LLM_MODEL"]
LLM_API_URL = os.environ["LLM_API_URL"]
client = instructor.from_provider(f"ollama/{LLM_MODEL}")


async def call_tools(message : Message, tool_registry:dict[str, Callable]) -> list[dict[str, Any]]:
    """
    Given a LiteLLM message, execute any tool calls made by the
    LLM and return their responses in an array. If no tool
    calls were made, returns an empty list.

    Args:
        message (Message): A LiteLLM message, obtainable via response.choices[0].message.
        tool_registry (dict[str, callable]): A dictionary mapping tool names to functions.
    
    Raises:
        HTTPException: If the LLM attempts to call a tool which does not exist, raises error 404.

    Returns:
        list[dict[str, Any]]: Tool responses. Each response has a "role", "content", and "tool_call_id" field.
    """
    if not message.tool_calls:
        return []

    tool_messages = []

    for tool_call in message.tool_calls:
        name = tool_call.function.name

        if name not in tool_registry:
            raise HTTPException(status_code=404, detail=f"LLM tool does not exist: {name}")
        
        if not tool_call.function.arguments:
            continue

        args = json.loads(tool_call.function.arguments)

        # Call the tool. If the tool is async, await the tool call.
        result = tool_registry[name](**args)
        if inspect.isawaitable(result):
            result = await result
        
        if type(result) is not str:
            raise HTTPException(status_code=500, detail=f"LLM tool {name} did not output a string result. All tool call results must be of string data type.")

        tool_messages.append({
            "role" : "tool",
            "tool_call_id" : tool_call.id,
            "content" : result
        })
    
    return tool_messages

PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}

def generate_tool_schema(fn : Callable) -> dict[str, Any]:
    """
    Generate an OpenAI tool schema for a given function in JSON format.
    See https://platform.openai.com/docs/guides/function-calling#defining-functions

    Args:
        fn (Callable): The function to generate a schema for.
    
    Raises:
        TypeError:
            All function arguments must have a type hint  

    Returns:
        dict[str, Any]: The function schema.
    """
    sig = inspect.signature(fn)
    type_hints = get_type_hints(fn)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name not in type_hints:
            raise TypeError(f"Missing type hint for parameter '{name}'")

        py_type = type_hints[name]
        json_type = PY_TO_JSON.get(py_type)

        if not json_type:
            raise TypeError(f"Unsupported type: {py_type}")

        properties[name] = {
            "type": json_type,
        }

        if param.default is inspect._empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": (fn.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }

def parse_tools(tool_functions : list[Callable]) -> tuple[list[dict], dict[str, Callable]]:
    """
    Convert a list of Python functions into a format usable for LLM tool calls.

    Args:
        tool_functions (list[Callable]):
            List of Python functions to convert into tool calls.
    
    Raises:


    Returns:
        tool_schema_list (list[dict]): List of OpenAI function definition JSON objects for each tool.
        tool_registry (dict[str, Callable]): A map of string names to tool functions.
    """ 
    tool_schema_list : list[dict] = []
    tool_registry : dict[str, Callable] = {}

    for tool_function in tool_functions:
        tool_name = tool_function.__name__
        tool_registry[tool_name] = tool_function
        
        tool_schema = generate_tool_schema(tool_function)
        tool_schema_list.append(tool_schema)

    return tool_schema_list, tool_registry

async def chat(
    messages : list[dict],
    system_prompt : str | None = SYSTEM_PROMPT,
    tools : list[Callable] = TOOLS,
    max_tool_calls : int = 5
) -> list[dict]:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
        system_prompt (str | None, optional): Optional system prompt to append to the beginning of the message list. Defaults to None.
        tools (list[Callable], optional): A list of tool definitions for the model. Defaults to [].
        max_tool_calls (int, optional): The maximum amount of times the LLM is permitted to execute tool calls. Defaults to 5.
    
    Raises:
        HTTPException: If something goes wrong in LiteLLM or Ollama, the exception is passed here.

    Returns:
        messages (lict[dict]): The list of messages with the assistant's response and chain of thought reasoning appended. 
    """
    
    tool_schema, tool_registry = parse_tools(tools)

    if system_prompt is not None:
        # If a system prompt is given, add it to the start of the messages
        messages.insert(0, {
            "role":"system",
            "content":system_prompt
        })
    
    try:

        tool_calls_used = 0

        while tool_calls_used < max_tool_calls:
            response = completion(
                model = f"ollama_chat/{LLM_MODEL}",
                api_base=LLM_API_URL,
                messages=messages,
                tools = tool_schema,
                tool_choice = "auto"
            )
            
            assistant_message = response.choices[0].message

            messages.append(assistant_message)
            
            # Call any tools that were requested by the LLM
            tool_messages = await call_tools(assistant_message, tool_registry=tool_registry)

            # If the LLM called any tools, add their result to the message list
            if tool_messages: messages.extend(tool_messages)

            # Otherwise, stop the LLM tool calling loop and return the last assistant message
            else: break
        
        return messages#response.choices[0].message.content 


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail= f"Error generating LLM response. Detail: {str(e)}"
        )

