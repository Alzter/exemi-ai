from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders, create_reminder
from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import ReminderCreate, ReminderPublic, User, Reminder
from .models_canvas import CanvasAssignment

def get_reminder_list(user : User, session : Session) -> str:
    """
    Obtain a plain text list of the user's current reminders.
    """
    reminders = get_reminders(offset=0, limit=100, user=user, session=session)

    if not reminders: return ""
    
    reminders = "\n\n".join(
        ["\n".join([
            f"Assignment name: {reminder.assignment_name}",
            f"Description: {reminder.description}",
            f"Due at: {reminder.due_at}"
        ])
    for reminder in reminders])
    
    return "The user has the following reminders: \n\n" + reminders.strip()


def get_system_prompt(user : User, magic : str, session : Session) -> str:
    return f"""
You are Exemi, a study assistance chatbot.
You are talking to an undergraduate university student who has been diagnosed with ADHD.

Your goal is to mentor the student in a friendly, non-judgemental way.

The current date is {parse_timestamp(datetime.now())}.

General rules:
- Always represent dates in the format: Monday, 8 February 2026.
- Respond in simple sentences. Break complex information or lists into bullet points.

Tool usage rules:
- When the user asks what assignments they have, call the tool get_assignments.
- Use the tool add_assignment_reminder to remind the user to complete an assignment.
- You may only call the tool add_assignment_reminder AFTER calling the tool get_assignments.
- You may only create ONE reminder per assignment.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the user in plain language.

{get_reminder_list(user=user, session=session)}
""".strip()

def cal_days_diff(a : datetime, b : datetime) -> int:
    """
    Calculate the number of calendar days between two dates.
    Source: Matt Alcock https://stackoverflow.com/a/17215747

    Args:
        a (datetime): Later date.
        b (datetime): Earlier date.
    
    Returns:
        days (int): The number of days between the dates.
    """
    A = a.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    B = b.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    return (A - B).days

def parse_timestamp(dt: datetime | None, australia_tz: str = "Australia/Sydney") -> str:
    """
    Converts a datetime (naive UTC or any tz-aware) to a specified
    Australian timezone and returns a human-readable string.

    Args:
        dt (datetime | None): Input datetime, can be naive (assumed UTC) or tz-aware.
        australia_tz (str, optional): Target Australian timezone. Defaults to "Australia/Sydney".

    Returns:
        str: Datetime string in the format: Monday, 08/02/2026, 05:30 PM (3 days from now)
    """

    if dt is None: return "Unknown"

    # Step 1: If naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Step 2: Convert to Australian timezone
    dt_aus = dt.astimezone(ZoneInfo(australia_tz))

    # Step 3: Format as readable string
    readable_str = dt_aus.strftime("%A, %d/%m/%Y, %I:%M %p")

    # Step 4: Add the number of days remaining
    current_time = datetime.now(ZoneInfo(australia_tz))
    days_difference = cal_days_diff(dt_aus, current_time)

    readable_str += f" ({days_difference} days from now)"

    return readable_str

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments() -> str:
        """
        Obtains the user's incomplete assignments.

        Returns:
            str: Description of the user's incomplete assignments.
        """
    
        assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)
        
        return "\n\n".join([
            "\n".join([
                f"Assignment name: {assignment.name}",
                f"Due at: {parse_timestamp(assignment.due_at)}"
            ])
        for assignment in assignments])
    
    @tool
    def add_assignment_reminder(assignment_name : str, due_at : datetime, description : str) -> str:
        """
        Create a reminder for the user to complete a given assignment.
        
        Args:
            assignment_name (str): The assignment name.
            due_at (datetime): The date to remind the user.
            description (str): What task the user needs to do. 
        
        Returns:
            str: Reminder creation success or failure message. 
        """
        
        data = ReminderCreate(assignment_name=assignment_name, due_at=due_at, description=description)

        try:
            reminder : Reminder = create_reminder(data, user=user, session=session)
            return "Reminder created successfully!"
        except Exception as e:
            return f"Error creating reminder. {str(e)}"
        
    return [get_assignments, add_assignment_reminder]

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

