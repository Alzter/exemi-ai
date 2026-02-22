from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders, create_reminder
from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import ReminderCreate, ReminderPublic, User, Reminder
from .models_canvas import CanvasAssignment
from .date_utils import parse_timestamp, timestamp_to_string 

def get_reminder_list(user : User, session : Session) -> str:
    """
    Obtain a plain text list of the user's current
    assignment reminders which are due in less
    than a week's time.
    """
    reminders = get_reminders(
        offset=0,
        limit=100,
        min_days_remaining=7,
        user=user,
        session=session
    )

    if not reminders: return ""
    
    reminders = "\n\n".join(
        ["\n".join([
            f"Assignment name: {reminder.assignment_name}",
            f"Description: {reminder.description}",
            f"Due at: {reminder.due_at}"
        ])
    for reminder in reminders])
    
    return "\n\n".join([
        "IMPORTANT: You have assigned the student the following assignment reminders:",
        reminders.strip(),
        "Please notify the student of these reminders."
    ])


def get_system_prompt(user : User, magic : str, session : Session) -> str:
    return f"""
You are Exemi, a study assistance chatbot.
You are talking to an undergraduate university student who has been diagnosed with ADHD.

Your goal is to help the student plan and manage their time.

The current date is {timestamp_to_string(datetime.now())}.

General rules:
- When responding to the user, represent dates in the format: Monday, 8 February 2026.
- Respond in simple sentences. Break complex information or lists into bullet points.

Tool usage rules:
- When using a tool, represent dates in ISO 8601 format (YYYY-MM-DD).
- When the user asks what assignments they have and you don't know yet, call the tool get_assignments.
- Use the tool add_assignment_reminder to remind the user to complete an assignment.
- You may only call the tool add_assignment_reminder AFTER calling the tool get_assignments.
- You may only create ONE reminder per assignment.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the user in plain language.

{get_reminder_list(user=user, session=session)}
""".strip()

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments_from_Canvas() -> str:
        """
        Obtains the user's incomplete assignments.

        Returns:
            str: Description of the user's incomplete assignments.
        """
    
        assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)
        
        return "\n\n".join([
            "\n".join([
                f"Assignment name: {assignment.name}",
                f"Due at: {timestamp_to_string(assignment.due_at)}"
            ])
        for assignment in assignments])
    
    @tool
    def add_assignment_reminder(assignment_name : str, due_date : str, description : str) -> str:
        """
        Create a reminder for the user to complete a given assignment.
        The dates should be provided in ISO 8601 format (YYYY-MM-DD).
        Do NOT create a reminder for an assignment if one already exists!
        
        Args:
            assignment_name (str): The assignment name.
            due_date (str): The date to remind the user in ISO 8601 format (YYYY-MM-DD).
            description (str): What task the user needs to do. 
        
        Returns:
            str: Reminder creation success or failure message. 
        """
        
        # Convert due date into an Australian timestamp
        due_at = datetime.fromisoformat(due_date)
        due_at = parse_timestamp(due_at)

        data = ReminderCreate(assignment_name=assignment_name, due_at=due_at, description=description)

        create_reminder(data, user=user, session=session)
        return "Reminder created successfully!"
        
    return [get_assignments_from_Canvas, add_assignment_reminder]

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

