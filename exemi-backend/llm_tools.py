from datetime import datetime
from langchain.tools import tool, BaseTool
from .routers.reminders import create_reminder, delete_reminder
from sqlmodel import Session
from .models import User, UserBiographyCreate, UserBiography, ReminderCreate
from .date_utils import parse_timestamp
from .dependencies import get_engine

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
    async def add_information_to_student_biography(information : str) -> str:
        """
        When the user discloses peronsal information
        such as their learning goals, strengths,
        or challenges, use this tool to remember this
        information for later. DO NOT use this tool to
        store the user's units, assignments, or assignment
        tasks; focus only on PERSONAL information. DO use
        this tool to remember the user's name, comorbidities,
        learning disorders, preferred study venues,
        effective study strategies, etc.

        Returns:
            str: Memory success message.
        """
        
        from .routers.users import update_user_biography

        new_bio : UserBiography = await update_user_biography(
            UserBiographyCreate(
                content=information
            ),
            max_words=300,
            user=user,
            session=session
        )

        return f"Student biography successfully updated."

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
        try:
            due_at = datetime.fromisoformat(due_date)
        except ValueError:
            return "Error creating reminder, please do NOT try again"

        due_at = parse_timestamp(due_at)

        if not due_at: return "Error creating reminder, please do NOT try again"

        data = ReminderCreate(assignment_name=task_name, due_at=due_at, description=description)

        try:
            # Use an isolated DB session for tool-side writes.
            # LangChain tool execution can re-enter request code paths, and
            # sharing the request-scoped session can trigger transaction-state
            # conflicts when commit() is called from inside a tool.
            with Session(get_engine()) as tool_session:
                create_reminder(data, user=user, session=tool_session)
            return "Reminder created successfully!"
        except Exception:
            return "Error creating reminder, please do NOT try again"
    
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
        try:
            with Session(get_engine()) as tool_session:
                delete_reminder(id=id, user=user, session=tool_session)
            return "Reminder deleted successfully!"
        except Exception:
            return "Error deleting reminder, please do NOT try again"

    return [set_reminder, remove_reminder, add_information_to_student_biography]
