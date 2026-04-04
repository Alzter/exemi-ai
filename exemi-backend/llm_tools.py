from datetime import datetime
from langchain.tools import tool, BaseTool
from .routers.reminders import create_reminder, delete_reminder
from .routers.tasks import create_task_for_self, update_task, delete_task
from sqlmodel import Session, select
from .models import User, UserBiographyCreate, UserBiography, ReminderCreate
from .models import Task, TaskPublic, TaskCreate, TaskUpdate, UsersAssignments
from .date_utils import parse_timestamp
from .dependencies import get_engine
from fastapi import HTTPException

def create_tools(
    user : User,
    session : Session
) -> list[BaseTool]:
    """
    Create LLM tools to manage database
    entities for the current user.

    Args:
        user (User): The current logged in user.
        session (Session): Connection to the SQL database.

    Returns:
        list[BaseTool]: The LLM tools.
    """

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
        
        with Session(get_engine()) as tool_session:
            await update_user_biography(
                UserBiographyCreate(
                    content=information
                ),
                max_words=300,
                user=user,
                session=tool_session
            )

        return "Student biography successfully updated."

    @tool
    def create_assignment_task_for_student(
        assignment_id : int,
        name : str,
        description : str,
        duration_mins : int,
        due_date : str
    ) -> str:
        """
        Create a task representing a small chunk
        of one of the student's assignments and
        assign this task to the student to complete
        on a specific date.

        Args:
            assignment_id (int): The ID number of the student's assignment which this task references.
            name (str): The name of the task in the format "<Shortened assignment name>: <Task name>".
            description (str): Summary of what steps are needed to complete the task.
            duration_mins (int): An estimation of how many minutes the student will need to complete this task.
            due_date (str): Which date the student must work on this task in ISO 8601 format (YYYY-MM-DD).

        Returns:
            str: Task creation success or failure message.
        """
        
        # Check the assignment given exists and that the user has it
        user_assignment = session.exec(
            select(UsersAssignments)
            .where(UsersAssignments.user_id == user.id)
            .where(UsersAssignments.assignment_id == assignment_id)
        )

        if not user_assignment:
            return f"Error creating task: the student does not have the assignment with ID {assignment_id}."

        # Convert due date into an Australian timestamp
        try:
            due_at = datetime.fromisoformat(due_date)
        except ValueError:
            return f"Error creating task: your due date {due_date} was not in the format YYYY-MM-DD."
        
        due_at = parse_timestamp(due_at)
        if not due_at:
            return f"Error creating task: your due date {due_date} was not in the format YYYY-MM-DD."

        data = TaskCreate(
            assignment_id = assignment_id,
            description = description,
            due_at = due_at,
            duration_mins = duration_mins
        )

        try:
            with Session(get_engine()) as tool_session:
                create_task_for_self(
                    data=data,
                    user=user,
                    session=tool_session
                )
            return "Task created successfully!"
        # Invalid task errors will throw a HTTPException
        except HTTPException as e:
            return f"Error creating task: {e.detail}"
        except Exception:
            return "Error creating task: database error. Do NOT try again."

    @tool
    def update_assignment_task_for_student(
        task_id : int,
        name : str | None = None,
        description : str | None = None,
        duration_mins : int | None = None,
        due_at : str | None = None
    ) -> str:
        """
        Update one of the student's assignment
        tasks by replacing one or more of its
        fields with new values.

        Args:
            task_id (int): ID of the task to modify.
            name (str | None, optional): New name for the task in the format "<Shortened assignment name>: <Task name>". Defaults to None.
            description (str | None, optional): New summary of what steps are needed to complete the task. Defaults to None.
            duration_mins (int | None, optional): New estimation of how many minutes the student will need to complete this task. Defaults to None.
            due_at (str | None, optional): New date the student must work on this task in ISO 8601 format (YYYY-MM-DD). Defaults to None.

        Returns:
            str: Task update success or failure message.
        """
        
        new_data = TaskUpdate(
            name=name,
            description=description,
            duration_mins=duration_mins,
            due_at=due_at
        )

        try:
            with Session(get_engine()) as tool_session:
                update_task(
                    id=task_id,
                    new_data=new_data,
                    user=user,
                    session=tool_session
                )
            return "Task updated successfully!"
        except HTTPException as e:
            return f"Error updating task: {e.detail}"
        except Exception:
            return "Error updating task. Do NOT try again."

    @tool
    def delete_assignment_task_for_student(
        task_id : int
    ) -> str:
        """
        Delete one of the student's assignment tasks.

        Args:
            task_id (int): ID of the task to delete.

        Returns:
            str: Task deletion success or failure message.
        """
        try:
            with Session(get_engine()) as tool_session:
                delete_task(
                    id=task_id,
                    user=user,
                    session=tool_session
                )
            return "Task deleted successfully!"
        except HTTPException as e:
            return f"Error deleting task: {e.detail}"
        except Exception:
            return "Error deleting task. Do NOT try again."

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
                delete_task(id=id, user=user, session=tool_session)
            return "Reminder deleted successfully!"
        except Exception:
            return "Error deleting reminder, please do NOT try again"

    return [
        create_assignment_task_for_student,
        update_assignment_task_for_student,
        delete_assignment_task_for_student,
        add_information_to_student_biography
    ]
