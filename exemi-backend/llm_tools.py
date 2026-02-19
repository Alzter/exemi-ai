from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import User
from .models_canvas import CanvasAssignment

def get_system_prompt() -> str:
    return f"""
You are Exemi, a study assistance chatbot for university students.
The current date is {parse_timestamp(datetime.now())}.

General rules:
- Always represent dates in the format: Monday, 8 February 2026, 16:30 AEDT

Tool usage rules:
- When the user asks what assignments they have, call the tool get_assignments.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the user in plain language.
""".strip()

def parse_timestamp(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> str:
    """
    Converts a datetime (naive UTC or any tz-aware) to a specified
    Australian timezone and returns a human-readable string.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        str: Formatted datetime string
    """

    if dt is None: return "Unknown"

    # Step 1: If naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Step 2: Convert to Australian timezone
    dt_aus = dt.astimezone(ZoneInfo(australia_tz))

    # Step 3: Format as readable string
    readable_str = dt_aus.strftime("%A, %d %B %Y, %H:%M %Z")

    return readable_str

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments() -> str:
        """
        Obtains the user's incomplete assignments.
        """
    
        assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)
        
        return "\n\n".join([
            f"Assignment name: {assignment.name}\nDue at: {parse_timestamp(assignment.due_at)}\nPoints: {assignment.points_possible}"
        for assignment in assignments])

    return [get_assignments]

# @tool
# async def get_weather(city : str) -> str:
#     """
#     Get the weather for a particular city.
# 
#     Args:
#         city (str): Which city to obtain the weather for.
# 
#     Returns:
#         The weather in degrees Celsius.
#     """
#     return "22 degrees Celsius"

