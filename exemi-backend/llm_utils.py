SYSTEM_PROMPT = """
You are a helpful, conversational chatbot.
You can answer general questions normally.
Tool usage rules:
- ONLY call the tool get_weather when the user explicitly asks about the current weather or temperature.
- If the user greets you or asks about your well-being, respond conversationally and DO NOT call any tools.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the user in plain language.
""".strip()

async def get_weather(city : str) -> str:
    return "22 degrees Celsius"

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
