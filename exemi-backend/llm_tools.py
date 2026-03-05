from datetime import datetime
from langchain.tools import tool, BaseTool
from .routers.reminders import create_reminder, delete_reminder
from sqlmodel import Session
from .models import User, ReminderCreate
from .date_utils import parse_timestamp

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
