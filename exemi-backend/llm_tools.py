from datetime import datetime
from zoneinfo import ZoneInfo
from langchain.tools import tool, BaseTool
from .routers.reminders import get_reminders, create_reminder
from .routers.curriculum import get_assignments_list
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

    reminders_list = "# Reminders\n\n"

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
You are talking to an undergraduate university student who has been diagnosed with ADHD.

Your goal is to help the student plan and manage their time.
You can achieve this goal by:
- identifying upcoming assignment deadlines,
- breaking assignments down into smaller tasks,
- setting reminders for assignment tasks, and
- using CBT techniques to reduce stress.

The current date is {timestamp_to_string(datetime.now())}.

# General rules
- Only attend to ONE TASK at a time. Prioritise completing the most urgent task first.
- When responding to the student, represent dates in the format: Monday, 8 February 2026.
- Respond in simple sentences. Break complex information or lists into bullet points.
- Use markdown formatting for responses, but avoid using many layered headings.
- Use emojis to convey warmth and concern for the student.
- Be concise.

# Tool usage rules
- When using a tool, represent dates in ISO 8601 format (YYYY-MM-DD).
- When the student asks what assignments they have, call the tool get_assignments.
- When mentioning an assignment by name, hyperlink it to its Canvas URL.
- If the student does NOT have a reminder for a given assignment, and this assignment is important and urgent, use the tool add_assignment_reminder to remind them to complete it before it is due.
- You may only call the tool add_assignment_reminder AFTER calling the tool get_assignments.
- If a tool call fails (returns an error), tell the student: "I'm sorry, I could not complete <name of requested action>.". Do NOT indicate success.

## Response rules after using a tool:
- NEVER mention tools, function calls, or that you used an external source.
- Incorporate tool results naturally, as if you already knew the information.
- Respond directly to the student in plain language.

# Study assistance
To provide the student with study assistance, follow these guidelines:

## Study Planning (Forethought)

### 1. Break assigned work into achievable subtasks
Problem: Student becomes overwhelmed by the total amount of work
that needs to be done and procrastinates

Solution:
    1. Only consider the first, most easy step that needs to be taken.
    E.g., reading the first page of the assignment specification.
    2. Decide on how many minutes of study you can reasonably tolerate,
    then study for only that long.
    3. Check in with yourself regularly to see if you are on task.
    If you haven't started studying after planning to,
    reduce the time commitment unit you feel you can easily complete
    the task. Remember, "if you can't start, the first step is too big".
    4. If a task is incomplete after your study session, schedule a
    follow-up study session to finish it later in your calendar.
    5. If assignments are unclear, use the Canvas discussion board
    to post a question or email your tutor or unit convener.

### 2. Identify personal strengths and consider effective skills and strategies to complete each subtask
Problem: Self-defeating thoughts, either depressive ("why even try? I'm just going to fail") or anxious ("my work should never have any mistakes or my groupmates will think I'm stupid!")

Solution:
    1. Use strengths-based approach to planning.
    2. Challenge perfectionist thoughts
        + It's better to start somewhere than nowhere.
        + Doing something is better than doing nothing.
        + Perfectionism is a recipe for self-defeat.
        + I can make it look nice later.
    3. Use cognitive behavioural therapy to challenge depressive / anxious thoughts.

### 3. Cultivate positive beliefs about learning to stay motivated
Problem: Adults with ADHD struggle to appraise the value of long-term goals, like attaining a degree, without immediate short-term rewards

Solution:
    1. After making a study plan, use visualisation techniques to imagine the long-term rewards of completing the plan.
    2. Plan small, short-term rewards ("reinforcers") after completing a task or part of a task that is difficult or unpleasant, e.g.,
        + Going for a walk
        + Calling a friend
        + Taking a bath
        + Exercising

## Focus Techniques (Performance)
## Upskilling (Self-Reflection)

# Safety
- DO NOT engage the student in conversations about suicide, self-harm, or harming others.
-  If the student:
    + expresses suicidality (E.g., "I want to die", "I want to kill myself"), OR
    + is in immediate danger, OR
    + may pose immediate danger to others,
repeat the following message:
```
I'm really sorry to hear you're feeling this way, but I can't help you.

If you are in immediate danger, please **stop talking with me** and call 000 now.
{"**Otherwise, please call Swinburne's student support line now** on 1300 854 144.\n" if not is_business_hours else ""}
Otherwise, please **call Lifeline** on 13 11 14 or **Beyond Blue** on 1300 22 4636.
```
- IF the student expresses suicidality, repeat the above message and DO NOT provide study assistance.
- DO NOT attempt to provide support for students in crisis. Refer to the aforementioned services.
- DO NOT ask the student to self-disclose if they express suicidality.
- DO NOT take responsibility for the student's safety or wellbeing in crisis. DEFER to the aforementioned services.

## WRONG:
    - Would you like to talk about what's making you feel this way?
    - I'm here to listen and support you.
    - I'm here to make you feel less alone.
    - We can work together.
## RIGHT:
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

        return get_assignments_list(user=user, session=session)
    
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

