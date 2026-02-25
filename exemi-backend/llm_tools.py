from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders, create_reminder
from .routers.curriculum import get_units, get_assignment_groups, get_assignments
# from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import Unit, AssignmentGroup, Assignment
from .models import User, Reminder, ReminderCreate, ReminderPublic
# from .models_canvas import CanvasAssignment
from .date_utils import parse_timestamp, timestamp_to_string, get_days_remaining_string

def get_reminder_list(user : User, session : Session) -> str:
    """
    Obtain a markdown-formatted list of the user's current
    assignment reminders which are due in less than two weeks
    time. If the user has no reminders, returns an empty string.
    
    Args:
        user (User): The currently logged-in user.
        session (Session): Connection to the database.

    Returns: Reminders list in a markdown format.
    """
    reminders : list[Reminder] = get_reminders(
        offset=0,
        limit=100,
        min_days_remaining=14,
        user=user,
        session=session
    )

    if not reminders: return ""
    
    reminders_list = "Remind the student to complete the following assignment tasks:\n"

    for reminder in reminders:
        days_remaining_string : str = get_days_remaining_string(reminder.due_at)

        reminders_list += "\n".join([
            f"\n- **{reminder.assignment_name}** ({days_remaining_string}):",
            f"{reminder.description}"
        ])

    return reminders_list.strip()

def get_greeting(
    user : User,
    magic : str,
    session : Session,
    is_first_conversation : bool
) -> str:
    """
    Unlike general-purpose chatbots, the Exemi chatbot initiates conversations
    with the user by sending an assistant message *first*. This function
    obtains the contents of the first assistant message to send the user
    to begin a conversation with them.

    Args:
        user (User): The currently logged-in user.
        magic (str): The user's magic.
        session (Session): A SQLModel connection with the backend database.
        is_first_conversation (bool): Whether this is the user's first conversation with the chatbot.

    Returns:
        str: Greeting message to begin user conversation.
    """

    if is_first_conversation:
        return """
Hi, I'm **Exemi**! I'm an AI chatbot designed to
help you plan and manage your time for your university course 😊

I can help you with:
- identifying upcoming assignment deadlines,
- breaking assignments down into smaller tasks,
- setting reminders for assignment tasks, and
- using practical strategies to reduce stress.

I am an **early prototype** of what could become a fully-featured AI
study assistant for students like you! Since I'm still in development,
**you may find issues or bugs** when using me. If this happens to you,
please let the researchers know in the feedback survey 👍
        """.strip()
    
    else:
        return f"## Hello! How can I help you today?"

def get_system_prompt(user : User, magic : str, session : Session) -> str:
    return f"""
You are Exemi, a study assistance chatbot.
You are talking to an undergraduate university student who has been diagnosed with ADHD.

Your goal is to help the student plan and manage their time.
You can achieve this goal by:
- identifying upcoming assignment deadlines,
- breaking assignments down into smaller tasks,
- setting reminders for assignment tasks, and
- using CBT techniques to reduce stress.

The current date is {timestamp_to_string(datetime.now())}.

General rules:
- Only attend to ONE TASK at a time. Prioritise completing the most urgent task first.
- When responding to the student, represent dates in the format: Monday, 8 February 2026.
- Respond in simple sentences. Break complex information or lists into bullet points.
- Use markdown formatting for responses, but avoid using many layered headings.
- Use emojis to convey warmth and concern for the student.
- Be concise.

Tool usage rules:
- When using a tool, represent dates in ISO 8601 format (YYYY-MM-DD).
- When the student asks what assignments they have, call the tool get_assignments.
- If the student does NOT have a reminder for a given assignment, and this assignment is important and urgent, use the tool add_assignment_reminder to remind them to complete it before it is due.
- You may only call the tool add_assignment_reminder AFTER calling the tool get_assignments.
- If a tool call fails (returns an error), tell the student: "I'm sorry, I could not complete <name of requested action>.". Do NOT indicate success.

Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the student in plain language.

{get_reminder_list(user=user, session=session)}
""".strip()

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments_from_Canvas() -> str:
        """
        Retrieve a list of the student's incomplete assignments.

        Returns:
            str: List of the student's incomplete assignments.
        """

        assignments = get_assignments(user=user, session=session)
        assignments = [AssignmentPublic.model_validate(a) for a in assignments]
        
        # assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)
        
        return "\n\n".join([
            "\n".join([
                f"Assignment name: {assignment.name}",
                f"Due at: {timestamp_to_string(assignment.due_at)}"
            ])
        for assignment in assignments])
    
    @tool
    def add_assignment_reminder(assignment_name : str, due_date : str, description : str) -> str:
        """
        Create a reminder for the student to complete a given assignment.
        The dates should be provided in ISO 8601 format (YYYY-MM-DD).
        Do NOT create a reminder for an assignment if one already exists!
        
        Args:
            assignment_name (str): The assignment name.
            due_date (str): The date to remind the student in ISO 8601 format (YYYY-MM-DD).
            description (str): What task the student needs to do. 
        
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

