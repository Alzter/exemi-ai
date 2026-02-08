from langchain.tools import tool, BaseTool
from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import User
from .models_canvas import CanvasAssignment

SYSTEM_PROMPT = """
You are Exemi, a study assistance chatbot for university students.

Tool usage rules:
- When the user asks what assignments they have, call the tool get_assignments.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the user in plain language.
""".strip()

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments() -> str:
        """
        Obtains the user's incomplete assignments.
        """
    
        assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)
        
        return "\n\n".join([
            f"Assignment name: {assignment.name}\nDue at: {assignment.due_at}\nPoints: {assignment.points_possible}"
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

