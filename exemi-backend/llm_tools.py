from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders_list_json, create_reminder, delete_reminder
from .routers.curriculum import get_assignments_list_json, get_units_list_json
# from .routers.canvas import canvas_get_all_assignments
from sqlmodel import Session
from .models import Unit, AssignmentGroup, Assignment
from .models import User, Reminder, ReminderCreate, ReminderPublic
# from .models_canvas import CanvasAssignment
from .date_utils import parse_timestamp, timestamp_to_string, get_days_remaining_string

def get_reminder_list(user : User, session : Session) -> str:
    """
    Obtain a JSON list of the student's current
    assignment reminders which are due in less
    than two weeks time.
    
    Args:
        user (User): The currently logged-in user.
        session (Session): Connection to the database.

    Returns: Reminders list in a markdown format.
    """

    reminders_list = get_reminders_list_json(
        user=user,
        session=session
    )

    if not reminders_list: return "##REMINDERS\n\nYou have not assigned the student any reminders yet."

    reminders = "## REMINDERS\n\nYou have assigned the student the following assignment reminders:\n\n"
    reminders += str(reminders_list)
    reminders += "\n\nNOTE: DO NOT mention the reminder IDs to the student."

    return reminders.strip()

def get_greeting(
    user : User,
    magic : str,
    session : Session,
    is_first_conversation : bool
) -> str:
    """
    Unlike general-purpose chatbots, the Exemi chatbot initiates conversations
    with the student by sending an assistant message *first*. This function
    obtains the contents of the first assistant message to send the student
    to begin a conversation with them.

    Args:
        user (User): The currently logged-in user.
        magic (str): The student's magic.
        session (Session): A SQLModel connection with the backend database.
        is_first_conversation (bool): Whether this is the student's first conversation with the chatbot.

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

    # Determine if the current time is within
    # business hours to determine if Swinburne's
    # after-hours student support phone line
    # is currently in operation.
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    weekday : int = now.weekday()
    is_weekend : bool = weekday > 4
    is_business_hours : bool = False
    if not is_weekend:
        if now.hour > 9 and now.hour < 17:
            is_business_hours = True

    return f"""
You are Exemi, a study assistance chatbot.
You are helping an undergraduate student from Swinburne University who has ADHD.

Your goal is to help the student plan, manage their time, and improve executive function.
You can achieve this goal by:
- identifying upcoming assignment deadlines from Canvas LMS,
- breaking assignments down into smaller tasks,
- setting reminders for upcoming tasks, and
- using CBT techniques to reduce stress.

The current date is {timestamp_to_string(datetime.now(ZoneInfo("Australia/Sydney")))}.

## GENERAL RESPONSE STYLE
- Simple sentences and language.
- Bullet points for lists of information.
- One task at a time.
- Date format: Monday, 8 February 2026.
- Use markdown formatting.
- Use emojis to convey warmth and concern for the student.
- Be concise.

## STUDY HELP RULES
Remember these principles for helping students with ADHD:
- If you're having trouble getting started, the first step is too big!
- Do all things in the order of priority.
- Start small, and begin with the easiest part.
- Work in a space free of distractions.
- Break study sessions into 25 minute chunks, or less if the task is hard.
- Replace depressive / anxious beliefs with more realistic ones.

{get_reminder_list(user=user, session=session)}

## TOOL USAGE RULES
- Tool dates must be in ISO 8601 format (YYYY-MM-DD).
- If a tool fails, say: "I'm sorry, I could not complete <action>."
- DO NOT indicate success or provide closure if a tool fails.
- Incorporate tool results naturally, as if you already knew the information.

## TASK PRIORITY RULES
1. Rank each assignment by urgency (LOWEST number of days remaining).
2. Rank each assignment by importance (HIGHEST grade contribution %).
3. Mention assignments which have less time left and greater grade contributions FIRST.
4. Ask the student which assignment they would like to prioritise first.

## UNITS
The student is enrolled in the following units:
{get_units_list_json(user=user, session=session)}

## ASSIGNMENTS
The student has the following assignments:
{get_assignments_list_json(user=user, session=session)}

## SAFETY
- DO NOT engage the student in conversations about suicide, self-harm, or harming others.
- If the student expresses suicidality (E.g., "I want to die", "I want to kill myself"), repeat the following message:
```
I'm really sorry to hear you're feeling this way, but I can't help you.

If you are in immediate danger, please **stop talking with me** and call 000 now.
{"**Otherwise, please call Swinburne's student support line now** on 1300 854 144.\n" if not is_business_hours else ""}
Otherwise, please **call Lifeline** on 13 11 14 or **Beyond Blue** on 1300 22 4636.
```
Do NOT use this safety message if the student is simply overwhelmed or stressed.
- IF the student expresses suicidality, repeat the above message and DO NOT provide study assistance.
- DO NOT attempt to provide support for students in crisis. Refer to the aforementioned services.
- DO NOT ask the student to self-disclose if they express suicidality.
- DO NOT take responsibility for the student's safety or wellbeing in crisis. DEFER to the aforementioned services.
""".strip()

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    # @tool
    # async def get_assignments_from_Canvas() -> str:
    #     """
    #     Retrieve a markdown-formatted list of the student's incomplete assignments.

    #     Returns:
    #         str: List of the student's incomplete assignments.
    #     """

    #     return str(get_assignments_list_json(user=user, session=session))
    
    @tool
    def set_reminder(task_name : str, due_date : str, description : str) -> str:
        """
        Create a reminder for the student to complete a task.
        The dates should be provided in ISO 8601 format (YYYY-MM-DD).
        
        Args:
            task_name (str): The name of the task to complete.
            due_date (str): The date to remind the student in ISO 8601 format (YYYY-MM-DD).
            description (str): What task the student needs to do. 
        
        Returns:
            str: Reminder creation success or failure message. 
        """
        
        # Convert due date into an Australian timestamp
        due_at = datetime.fromisoformat(due_date)
        due_at = parse_timestamp(due_at)

        if not due_at: return "Error creating reminder, please do NOT try again"

        data = ReminderCreate(assignment_name=task_name, due_at=due_at, description=description)

        create_reminder(data, user=user, session=session)
        return "Reminder created successfully!"
    
    @tool
    def remove_reminder(id : int) -> str:
        """
        Remove one of the student's active reminders.
        Use this tool when the student has completed
        the task you reminded them to do.

        Args:
            id (int): The ID of the reminder to remove.

        Returns:
            str: Reminder deletion success or failure message.
        """
        delete_reminder(id=id, user=user, session=session)
        return "Reminder deleted successfully!"

    return [set_reminder, remove_reminder]
