import json
import inspect
from typing import Callable, Any
from fastapi import APIRouter, Depends, HTTPException, Query
import litellm
from litellm import completion
from litellm.types.utils import Message
import instructor
from pydantic import BaseModel

async def get_weather(city : str) -> str:
    return "22 degrees Celsius"

SYSTEM_PROMPT = (
    "You are a helpful, conversational chatbot.\n"
    "You can answer general questions normally.\n\n"

    "Tool usage rules:\n"
    "- ONLY call the tool get_weather when the user explicitly asks about the current weather or temperature.\n"
    "- If the user greets you or asks about your well-being, respond conversationally and DO NOT call any tools.\n\n"

    "Response rules after using a tool:\n"
    "- NEVER mention tools, function calls, or that you used an external source.\n"
    "- Incorporate tool results naturally, as if you already knew the information.\n"
    "- Respond directly to the user in plain language."
)


TOOL_REGISTRY = { 
    "get_weather" : get_weather
}

TOOL_SCHEMA = [{
    "type" : "function",
    "function" : {
        "name" : "get_weather",
        "description" : "Get the current weather",
        "parameters": {
            "type":"object",
            "properties":{
                "city": {
                    "type": "string",
                    "description": "The name of the city"
                    }
                }
            },
            "required":["city"],
    }
}]

MODEL = "llama3.1:8b"
LLM_API_URL = "http://localhost:11434"
client = instructor.from_provider(f"ollama/{MODEL}")

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

# @router.get("/llm/chat{messages}")
async def chat(
    messages : list[dict],
    system_prompt : str | None = SYSTEM_PROMPT,
    tool_schema : list[dict] = TOOL_SCHEMA,
    tool_registry : dict[str, Callable] = TOOL_REGISTRY,
    max_tool_calls : int = 5
) -> str:
    """
    Call the LLM to respond to the user's message(s).
    Supports tool calling in a loop (so-called agentic AI).
    
    Args:
        messages (list[dict]): List of messages in OpenAI format.
        system_prompt (str|None): Optional system prompt to append to the beginning of the message list.
        tool_schema (list[dict]): A list of callable tools for the model. See https://platform.openai.com/docs/guides/function-calling#defining-functions
        tool_registry (dict[str, Callable]): A dictionary mapping tool names to functions.
        max_tool_calls (int): The maximum amount of times the LLM is permitted to execute tool calls.
    
    Raises:
        HTTPException: If something goes wrong in LiteLLM or Ollama, the exception is passed here.

    Returns:
        str: The content of the assistant's final message.
    """
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
                model = f"ollama_chat/{MODEL}",
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
        
        return response.choices[0].message.content 


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail= f"Error generating LLM response. Detail: {str(e)}"
        )

