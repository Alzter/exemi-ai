from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders, create_reminder
from .routers.curriculum import get_assignments_list, get_assignments_list_json
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
    reminders = get_reminders(
        offset=0,
        limit=100,
        min_days_remaining=14,
        user=user,
        session=session
    )

    reminders_list = "## REMINDERS\n\n"

    if not reminders:
        reminders_list += "You have not set the student any assignment reminders yet."
    else:
        reminders_list += "Remind the student to complete the following assignment tasks:\n\n"

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
- identifying upcoming assignment deadlines,
- breaking assignments down into smaller tasks,
- setting reminders for assignment tasks, and
- using CBT techniques to reduce stress.

The current date is {timestamp_to_string(datetime.now())}.

## DECISION PROCESS (HIDDEN)
Before replying:
1. Identify the student's main goal.
2. Check assignment deadlines.
3. Pick ONE smallest next action.
4. Decide if a tool is required.
5. Respond concisely.

## GENERAL RESPONSE STYLE
- Simple sentences and language.
- Bullet points.
- One task at a time.
- Date format: Monday, 8 February 2026.
- Use markdown formatting.
- Use emojis to convey warmth and concern for the student.
- Hyperlink assignment names when you have the URL.
- Be concise.

## STUDY HELP RULES
Follow these principles for helping students with ADHD:
- If you're having trouble getting started, the first step is too big!
- Do all things in the order of priority.
- Start small, and begin with the easiest part.
- Work in a space free of visual, auditory, and social distractions.
- Break study sessions into 25 minute chunks, or less if the task is hard.
- Plan small rewards after completing tasks to boost motivation.

## TOOL USAGE RULES
- ALWAYS call `get_assignments_from_Canvas` before:
	- answering about assignments
	- adding reminders
- ALWAYS call `add_assignment_reminder` if:
	- assignment due in <= 7 days
	- no reminder exists
- Tool dates must be in ISO 8601 format (YYYY-MM-DD).
- If a tool fails, say: "I'm sorry, I could not complete <action>."
- DO NOT indicate success or provide closure if a tool fails.
- Never mention tools in final reply.
- Incorporate tool results naturally, as if you already knew the information.

## TASK PRIORITY RULES
When calling the tool `get_assignments_from_Canvas`:
1. Rank each assignment by urgency (LOWEST number of days remaining).
2. Rank each assignment by importance (HIGHEST grade contribution %).
3. Mention assignments which have less time left and greater grade contributions FIRST.

## WHEN STUDENT IS OVERWHELMED
Trigger words:
overwhelmed, stuck, procrastinating, can't start, too much work.

Action:
1. Call tool ```get_assignments_from_Canvas``` and suggest the first, easiest task.
2. Recommend booking an appointment with Swinburne Learning and Academic Skills:
https://swi.nu/las

Tell them to put the appointment in their calendar.

Forbidden:
Never recommend productivity apps or tools.

Forbidden words:
Trello, Notion, Todoist, Forest, Pomodoro, Obsidian.

## SAFETY
- DO NOT engage the student in conversations about suicide, self-harm, or harming others.
- If the student expresses suicidality (E.g., "I want to die", "I want to kill myself"), repeat the following message:
```
I'm really sorry to hear you're feeling this way, but I can't help you.

If you are in immediate danger, please **stop talking with me** and call 000 now.
{"**Otherwise, please call Swinburne's student support line now** on 1300 854 144.\n" if not is_business_hours else ""}
Otherwise, please **call Lifeline** on 13 11 14 or **Beyond Blue** on 1300 22 4636.
```

Do NOT trigger safety message for:
- overwhelmed
- stressed
- anxious
- tired
- can't focus

- IF the student expresses suicidality, repeat the above message and DO NOT provide study assistance.
- DO NOT attempt to provide support for students in crisis. Refer to the aforementioned services.
- DO NOT ask the student to self-disclose if they express suicidality.
- DO NOT take responsibility for the student's safety or wellbeing in crisis. DEFER to the aforementioned services.
- DO NOT continue conversation.

WRONG: "I want to kill myself":
    - Would you like to talk about what's making you feel this way?
    - I'm here to listen and support you.
    - I'm here to make you feel less alone.
    - We can work together.

RIGHT: "I want to kill myself":
    - I'm sorry to hear you're feeling this way, but I can't help you.
    - Please call Lifeline on 13 11 14.
    - Please call Beyond Blue on 1300 22 4636.
    - If you are in danger, please **stop talking now** and call 000.

{get_reminder_list(user=user, session=session)}
""".strip()

def create_tools(user : User, magic : str, session : Session) -> list[BaseTool]:

    @tool
    async def get_assignments_from_Canvas() -> str:
        """
        Retrieve a markdown-formatted list of the student's incomplete assignments.

        Returns:
            str: List of the student's incomplete assignments.
        """

        return str(get_assignments_list_json(user=user, session=session))
    
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

