from ..models import TaskAutofillCreate, User, UsersAssignments
from ..models import Task, TaskCreate, TaskUpdate, TaskPublic, TaskList, TaskLLM
from ..models import Assignment, AssignmentGroup, Unit
from typing import Literal
from sqlmodel import Session, select
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_current_user, get_current_magic
from ..date_utils import parse_timestamp
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pydantic import BaseModel, TypeAdapter
import warnings

router = APIRouter()

def _utc_naive_bounds_for_local_calendar_day(
    d: date, timezone_name: str
) -> tuple[datetime, datetime]:
    """
    Inclusive start and exclusive end of calendar day ``d`` in ``timezone_name``,
    as naive UTC datetimes for comparison with ``Task.due_at`` (stored as UTC wall time).
    Avoids MariaDB ``CONVERT_TZ``, which returns NULL when named time zone tables are missing.
    """
    tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(d, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )

def _require_valid_timezone(timezone_name: str) -> None:
    try:
        ZoneInfo(timezone_name)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone_name")


def user_has_incomplete_overdue_tasks_sydney(
    username: str,
    user: User,
    session: Session,
    timezone_name: str = "Australia/Sydney",
) -> bool:
    """True if the user has any incomplete task due before local calendar today (matches prompt timezone)."""
    tasks = get_all_tasks_for_user(
        username=username,
        incomplete_only=True,
        offset=0,
        limit=100,
        user=user,
        session=session,
    )
    today = datetime.now(ZoneInfo(timezone_name)).date()
    start_naive, _ = _utc_naive_bounds_for_local_calendar_day(today, timezone_name)
    for t in tasks:
        if t.due_at is not None and t.due_at < start_naive:
            return True
    return False


def get_incomplete_tasks_as_task_list(
    username: str,
    user: User,
    session: Session,
) -> TaskList:
    """Map DB tasks to TaskList for LLM bypass (skips tasks without assignment_id)."""
    tasks = get_all_tasks_for_user(
        username=username,
        incomplete_only=False,
        offset=0,
        limit=100,
        user=user,
        session=session,
    )
    out: list[TaskLLM] = []
    for t in tasks:
        if t.assignment_id is None:
            continue
        out.append(
            TaskLLM(
                id=t.id,
                assignment_id=t.assignment_id,
                name=t.name,
                description=t.description,
                duration_mins=t.duration_mins,
                due_at=t.due_at,
                completed=t.completed,
            )
        )
    return TaskList(tasks=out)


def save_tasks_generation_assignments_snapshot(username: str, session: Session) -> None:
    from ..routers.curriculum import build_assignments_payload, snapshot_assignments_json

    u = session.exec(select(User).where(User.username == username)).first()
    if not u:
        return
    payload = build_assignments_payload(user=u, session=session)
    u.tasks_generation_assignments_snapshot = snapshot_assignments_json(payload)
    session.add(u)
    session.commit()


@router.get("/task/{id}", response_model=TaskPublic)
def get_task(
    id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    """
    Obtains a given task by ID.

    Args:
        id (int): ID of the task to obtain.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 404 if the task was not found.
        HTTPException: Raises a 404 if a non-adminstrator user attempts to read another user's task.

    Returns:
        Task: _description_
    """
    task = session.get(Task, id)
    if not task: raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != user.id and not user.admin:
        # Don't return tasks from other users unless the user is an admin
        raise HTTPException(status_code=404, detail="Task not found")

    return task

@router.get("/tasks_all/self", response_model=list[TaskPublic])
def get_all_tasks_for_self(
    incomplete_only : bool = False,
    unit_id : int | None = None,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> list[Task]:
    """
    Obtain all incomplete and complete tasks for the current user.

    Args:
        incomplete_only (booll, optional): Whether to only return incomplete tasks.
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        list[Task]: The list of tasks.
    """
    return get_all_tasks_for_user(
        username=user.username,
        incomplete_only=incomplete_only,
        unit_id=unit_id,
        offset=offset,
        limit=limit,
        user=user,
        session=session,
    )

@router.get("/tasks_all/{username}", response_model=list[TaskPublic])
def get_all_tasks_for_user(
    username : str,
    incomplete_only : bool = False,
    unit_id : int | None = None,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> list[Task]:
    """
    Obtain all incomplete and complete tasks for an arbitrary user.

    Args:
        username (str): Which user to obtain task list for.
        incomplete_only (bool, optional): Whether to only return incomplete tasks.
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        list[Task]: The list of tasks.
    """
    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")
    
    query = select(Task)
    query = query.join(User)
    query = query.where(User.username==username)

    if incomplete_only:
        query = query.where(Task.completed == False)

    if unit_id:
        query = query.join(Assignment)
        query = query.join(AssignmentGroup)
        query = query.join(Unit)
        query = query.where(Unit.id == unit_id)

    query = query.order_by(Task.due_at)
    query = query.offset(offset)
    query = query.limit(limit)

    tasks = session.exec(query)

    return tasks

class TaskJSON(BaseModel):
    id : int
    assignment_id : int | None
    name : str
    description : str
    duration_mins : int
    due_at : datetime
    completed : bool

tasks_list_adapter = TypeAdapter(list[TaskJSON])

@router.get("/tool/tasks_json/self", response_model=str)
def get_tasks_list_for_self_json(
    incomplete_only : bool = False,
    unit_id : int | None = None,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> str:
    """
    For the current user, obtain a string
    representing list of JSON objects for
    each of their incomplete tasks.

    Args:
        incomplete_only (bool, optional): Whether to only return incomplete tasks. Defaults to False.
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        str: The tasks list JSON string.
    """
    return get_tasks_list_for_user_json(
        username=user.username,
        incomplete_only=incomplete_only,
        unit_id=unit_id,
        user=user,
        session=session
    )

@router.get("/tool/tasks_json/{username}", response_model=str)
def get_tasks_list_for_user_json(
    username : str,
    incomplete_only : bool = False,
    unit_id : int | None = None,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> str:
    """
    For any user, obtain a string
    representing list of JSON objects for
    each of their tasks.

    Args:
        username (str): User to obtain task list for.
        incomplete_only (bool, optional): Whether to only return incomplete tasks. Defaults to False.
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        str: The tasks list JSON string.
    """
    tasks = get_all_tasks_for_user(
        username=username,
        incomplete_only=incomplete_only,
        unit_id=unit_id,
        offset=0,
        limit=100,
        user=user,
        session=session
    )

    tasks_json = [
        TaskJSON(
            id = task.id,
            assignment_id = task.assignment_id,
            name = task.name,
            description = task.description,
            duration_mins = task.duration_mins,
            due_at = task.due_at,
            completed = task.completed
        )
    for task in tasks]

    return tasks_list_adapter.dump_json(tasks_json).decode("utf-8")

@router.get("/tasks/self", response_model=list[TaskPublic])
def get_tasks_for_self(
    date: datetime = datetime.now(timezone.utc),
    current_date: datetime = datetime.now(timezone.utc),
    timezone_name: str = "Australia/Sydney",
    unit_id : int | None = None,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[TaskPublic]:
    """
    Obtain a list of tasks for the current user.
    Automatically pushes overdue tasks into the
    current day.

    RULES:
    ---------
    When obtaining tasks for the current day,
    all incomplete tasks are obtained as well
    as all tasks which were completed on that
    day.

    When obtaining tasks for a date in the future,
    only incomplete tasks are retrieved for that day.

    When obtaining tasks for a date in the past,
    only complete tasks are retrieved for that day.

    Args:
        date (datetime, optional): What date to obtain tasks for. Defaults to datetime.now(timezone.utc).
        current_date (datetime, optional):
            What date it is today.
            Used to determine if we are searching in the future for incomplete tasks,
            in the past for complete tasks, or in the present for incomplete tasks and all tasks
            which were completed today. Defaults to datetime.now(timezone.utc).
        timezone_name (str, optional)>
            What timezone the user is located in.
            Needed so that each day starts at 12:00 AM
            for the user. Defaults to "Australia/Sydney".
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        list[Task]: The list of tasks.
    """
    return get_tasks_for_user(
        username=user.username,
        date=date,
        current_date=current_date,
        timezone_name=timezone_name,
        unit_id=unit_id,
        offset=offset,
        limit=limit,
        user=user,
        session=session,
    )

@router.get("/tasks/{username}", response_model=list[TaskPublic])
def get_tasks_for_user(
    username: str,
    date: datetime = datetime.now(timezone.utc),
    current_date: datetime = datetime.now(timezone.utc),
    timezone_name: str = "Australia/Sydney",
    unit_id : int | None = None,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Task]:
    """
    Obtain a list of tasks for an arbitrary user.
    Automatically pushes overdue tasks into the
    current day.

    RULES:
    ---------
    When obtaining tasks for the current day,
    all incomplete tasks are obtained as well
    as all tasks which were completed on that
    day.

    When obtaining tasks for a date in the future,
    only incomplete tasks are retrieved for that day.

    When obtaining tasks for a date in the past,
    only complete tasks are retrieved for that day.

    Args:
        username (str): Which user to obtain task list for.
        date (datetime, optional): What date to obtain tasks for. Defaults to datetime.now(timezone.utc).
        current_date (datetime, optional):
            What date it is today.
            Used to determine if we are searching in the future for incomplete tasks,
            in the past for complete tasks, or in the present for incomplete tasks and all tasks
            which were completed today. Defaults to datetime.now(timezone.utc).
        timezone_name (str, optional)>
            What timezone the user is located in.
            Needed so that each day starts at 12:00 AM
            for the user. Defaults to "Australia/Sydney".
        unit_id (int | None, optional): If given, only select tasks for this unit. Defaults to None.
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 401 if a non-administrator user tries to read another user's task list.

    Returns:
        list[Task]: The list of tasks.
    """
    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    _require_valid_timezone(timezone_name)

    current_local = parse_timestamp(current_date, australia_tz=timezone_name)
    target_local = parse_timestamp(date, australia_tz=timezone_name)
    if current_local is None or target_local is None:
        raise HTTPException(status_code=400, detail="Invalid date")

    today_date = current_local.date()
    target_date = target_local.date()

    is_present = target_date == today_date
    is_future = target_date > today_date
    is_past = target_date < today_date

    query = (
        select(Task)
        .join(User)
        .where(User.username == username)
        .options(selectinload(Task.user), selectinload(Task.assignment))
    )

    if unit_id:
        query = query.join(Assignment)
        query = query.join(AssignmentGroup)
        query = query.join(Unit)
        query = query.where(Unit.id == unit_id)

    if is_present:
        today_start, today_end = _utc_naive_bounds_for_local_calendar_day(
            today_date, timezone_name
        )
        query = query.where(
            or_(
                and_(Task.completed == False, Task.due_at < today_end),
                and_(
                    Task.completed == True,
                    Task.due_at >= today_start,
                    Task.due_at < today_end,
                ),
            )
        )
    elif is_future:
        ts, te = _utc_naive_bounds_for_local_calendar_day(target_date, timezone_name)
        query = query.where(
            and_(Task.completed == False, Task.due_at >= ts, Task.due_at < te)
        )
    elif is_past:
        ts, te = _utc_naive_bounds_for_local_calendar_day(target_date, timezone_name)
        query = query.where(
            and_(Task.completed == True, Task.due_at >= ts, Task.due_at < te)
        )

    query = query.order_by(Task.due_at).offset(offset).limit(limit)

    tasks = session.exec(query).all()

    return tasks


@router.post("/task/{username}", response_model=TaskPublic)
def create_task_for_user(
    username: str,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    """
    Create a new task for any given user.

    Args:
        username (str): Name of the user to create a task for.
        data (TaskCreate): Data of the new task to create
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 401 if a non-administrator user tries to create tasks on behalf of another user.
        HTTPException: Raises a 404 if the user specified by 'username' is not found.
        HTTPException: Raises a 400 if the task's owner does not have the task's assignment.
        HTTPException: Raises a 400 if the task's due date is earlier than the current date.
        HTTPException: Raises a 400 if the task's due date is later than the assignment's due date.

    Returns:
        Task: The new task.
    """
    
    # Do not allow task creation on behalf of other users unless admin
    existing_user = user

    if user.username != username:
        if not user.admin:
            raise HTTPException(status_code=401, detail="Unauthorised")

        existing_user = session.exec(
            select(User).where(User.username == username)
        ).first()

        if not existing_user:
            raise HTTPException(status_code=404, detail=f"User not found: {username}")

    # Ensure the task due date is later than or equal to the current date
    # current_date = datetime.now(ZoneInfo("Australia/Sydney"))
    # if parse_timestamp(data.due_at) < current_date:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"The task due date ({parse_timestamp(data.due_at).date().isoformat()}) cannot be earlier than the current date ({current_date.date().isoformat()})"
    #     )

    if data.assignment_id is not None:
        # Ensure the task due date is earlier than the assignment due date
        existing_assignment = session.exec(
            select(UsersAssignments)
            .where(UsersAssignments.user_id == existing_user.id)
            .where(UsersAssignments.assignment_id == data.assignment_id)
        ).first()

        if not existing_assignment:
            raise HTTPException(
                status_code=400,
                detail=f"The student does not have the assignment with ID {data.assignment_id}",
            )
        
        # existing_assignment_data = existing_assignment.assignment

        # if parse_timestamp(data.due_at) > parse_timestamp(existing_assignment_data.due_at):
        #     raise HTTPException(
        #         status_code=400,
        #         detail=f"The task due date ({parse_timestamp(data.due_at).date().isoformat()}) cannot be later than the assignment due date ({parse_timestamp(existing_assignment_data.due_at).date().isoformat()})"
        #     )

    task = Task.model_validate(
        data,
        update={
            "user_id": existing_user.id,
            "created_at": datetime.now(timezone.utc),
            "completed": False,
            "in_progress": False,
        },
    )

    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@router.post("/task", response_model=TaskPublic)
def create_task_for_self(
    data: TaskCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    """
    Create a new task for the current user.

    Args:
        data (TaskCreate): Data of the new task to create
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 400 if the user does not have the task's assignment.
        HTTPException: Raises a 400 if the task's due date is earlier than the current date.
        HTTPException: Raises a 400 if the task's due date is later than the assignment's due date.

    Returns:
        Task: The new task.
    """
    return create_task_for_user(
        username=user.username,
        data=data,
        user=user,
        session=session,
    )

@router.post("/task_autofill/self", response_model=TaskCreate)
async def autocomplete_task_for_self(
    data : TaskAutofillCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> TaskCreate:
    """
    For the current user, create a task and add it
    to their list of assignment tasks when given only
    a task name and due date without fields for its
    description, assignmennt ID, and duration by using
    the LLM to autocomplete the missing fields by
    referencing the student's assignments list.

    Args:
        data (TaskAutofillCreate): Incomplete TaskCreate object with only name and due date.
        user (User): The currently logged in user.
        session (Session): Connection to the SQL database.
    
    Returns:
        TaskCreate: The task creation object with missing fields completed.
        Task: The task object created in the database.
    """
    task = await autocomplete_task_for_user(
        username = user.username,
        data=data,
        user=user,
        session=session
    )
    return task

@router.post("/task_autofill/{username}", response_model=TaskCreate)
async def autocomplete_task_for_user(
    data : TaskAutofillCreate,
    username : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> TaskCreate:
    """
    For an arbitrary user, create a task and add it
    to their list of assignment tasks when given only
    a task name and due date without fields for its
    description, assignmennt ID, and duration by using
    the LLM to autocomplete the missing fields by
    referencing the student's assignments list.

    Args:
        data (TaskAutofillCreate): Incomplete TaskCreate object with only name and due date.
        username (username): User to create task on behalf of.
        user (User): The currently logged in user.
        session (Session): Connection to the SQL database.

    Raises:
        HTTPException: Raises a 401 if a non-adminstrator user attempts to create tasks on behalf of another user.
        HTTPException: Raises a 404 if the user specified by username was not found.
    
    Returns:
        TaskCreate: The task creation object with missing fields completed.
        Task: The task object created in the database.
    """
    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    from ..llm_api import autofill_task_for_user

    data_with_fields : TaskCreate = await autofill_task_for_user(
        task = data,
        username=username,
        user=user,
        session=session
    )

    # task : Task = create_task_for_user(
    #     data=data_with_fields,
    #     username=username,
    #     user=user,
    #     session=session
    # )

    return data_with_fields

@router.patch("/task/{id}", response_model=TaskPublic)
def update_task(
    id: int,
    new_data: TaskUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Task:
    """
    Modify the fields of a given task, such as its duration or completion status.

    Args:
        id (int): ID of the task to update.
        new_data (TaskUpdate): Fields of the task to overwrite.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 404 if the task was not found.
        HTTPException: Raises a 404 if a non-adminstrator user attempts to update another user's task.
        HTTPException: Raises a 400 if the task's owner does not have the task's assignment.
        HTTPException: Raises a 400 if the task's due date is earlier than the current date.
        HTTPException: Raises a 400 if the task's due date is later than the assignment's due date.

    Returns:
        Task: The updated task.
    """
    
    task = get_task(id=id, user=user, session=session)
    
    # Ensure the user owning this task exists
    existing_user = session.get(User, task.user_id)
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"The task's owner was not found under user ID {task.user_id}")

    # due_at = new_data.due_at if new_data.due_at is not None else task.due_at
    # Only enforce "due not in the past" when the client changes due_at (completion toggles must work for older tasks).
    # if new_data.due_at is not None and due_at is not None:
    #     current_date = datetime.now(ZoneInfo("Australia/Sydney"))
    #     if parse_timestamp(due_at) < current_date:
    #         raise HTTPException(
    #             status_code=400,
    #             detail=f"The task due date ({parse_timestamp(due_at).date().isoformat()}) cannot be earlier than the current date ({current_date.date().isoformat()})"
    #         )

    # Check the user has the assignment which this task references
    assignment_id = new_data.assignment_id if new_data.assignment_id is not None else task.assignment_id

    # Ensure the task due date is earlier than the assignment due date
    if assignment_id:
        existing_assignment = session.exec(
            select(UsersAssignments)
            .where(UsersAssignments.user_id == existing_user.id)
            .where(UsersAssignments.assignment_id == assignment_id)
        ).first()
        if not existing_assignment:
            raise HTTPException(
                status_code=400,
                detail=f"The student does not have the assignment with ID {assignment_id}",
            )
        # existing_assignment_data = existing_assignment.assignment

        # if parse_timestamp(due_at) > parse_timestamp(existing_assignment_data.due_at):
        #     raise HTTPException(
        #         status_code=400,
        #         detail=f"The task due date ({parse_timestamp(due_at).date().isoformat()}) cannot be later than the assignment due date ({parse_timestamp(existing_assignment_data.due_at).date().isoformat()})"
        #     )

    new_data_dict = new_data.model_dump(exclude_unset=True)
    task.sqlmodel_update(new_data_dict)
    session.add(task)
    session.commit()
    session.refresh(task)

    return task

@router.delete("/task/{id}", response_model=Literal[True])
def delete_task(
    id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Literal[True]:
    """
    Delete a given task.

    Args:
        id (int): ID of the task to delete.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 404 if the task was not found.
        HTTPException: Raises a 404 if a non-adminstrator user attempts to delete another user's task.

    Returns:
        Literal[True]: Success.
    """

    task = get_task(id=id, user=user, session=session)

    session.delete(task)
    session.commit()
    return True

@router.delete("/tasks/self", response_model=Literal[True])
def delete_tasks_for_self(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> Literal[True]:
    """
    Delete all tasks for the current user.
    """
    return delete_tasks_for_user(
        username=user.username,
        user=user,
        session=session
    )

@router.delete("/tasks/{username}", response_model=Literal[True])
def delete_tasks_for_user(
    username : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> Literal[True]:
    """
    Delete all tasks for an arbitrary user.

    Args:
        username (str): Name of the user to delete tasks for.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 401 if a non-administrator user attempts to delete another user's tasks.
        HTTPException: Raises a 404 if the user specified by 'username' is not found.

    Returns:
        Literal[True]: Success.
    """

    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    existing_tasks : list[Task] = get_all_tasks_for_user(
        username=username,
        incomplete_only=False,
        offset=0,
        limit=100,
        user=user,
        session=session
    )
    
    for task in existing_tasks:
        session.delete(task)
    
    # Clear out the user's cached snapshot of assignment tasks
    user.tasks_generation_assignments_snapshot = None
    session.add(user)

    session.commit()
    return True

class TaskGenerationResult(BaseModel):
    generated_tasks : list[TaskLLM]
    updated_tasks_list : list[TaskPublic]

@router.post("/tasks/cleanup/self", response_model=list[TaskPublic])
def cleanup_tasks_for_self(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> list[Task]:
    """
    Cleanup the current user's tasks list by deleting
    all tasks which no longer reference an assignment
    the user has.

    Args:
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException:
            Raises a 401 if a non-administrator user attempts to cleanup another user's tasks.
        HTTPException:
            Raises a 404 if the user specified by 'username' is not found.

    Returns:
        list[Task]: The user's updated list of tasks.
    """
    return cleanup_tasks_for_user(
        username=user.username,
        user=user,
        session=session
    )

@router.post("/tasks/cleanup/{username}", response_model=list[TaskPublic])
def cleanup_tasks_for_user(
    username : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> list[Task]:
    """
    Cleanup an arbitrary user's tasks list by deleting
    all tasks which no longer reference an assignment
    the user has.

    Args:
        username (str): Name of the user to cleanup tasks for.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException:
            Raises a 401 if a non-administrator user attempts to cleanup another user's tasks.
        HTTPException:
            Raises a 404 if the user specified by 'username' is not found.

    Returns:
        list[Task]: The user's updated list of tasks.
    """

    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    existing_user = session.exec(
        select(User)
        .where(User.username==username)
    ).first()
    
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User not found: {username}")

    existing_tasks : list[Task] = get_all_tasks_for_user(
        username=username,
        incomplete_only=False,
        offset=0,
        limit=100,
        user=user,
        session=session
    )

    user_assignments : list[UsersAssignments] = session.exec(
        select(UsersAssignments)
        .where(UsersAssignments.user_id == existing_user.id)
    ).all()

    user_assignments_by_id : dict[int, UsersAssignments] = {assignment.assignment_id : assignment for assignment in user_assignments}

    existing_tasks_by_id : dict[int, Task] = {task.id : task for task in existing_tasks}
    for task_id, task in existing_tasks_by_id.items():

        if task.assignment_id is not None:
            existing_assignment = user_assignments_by_id.get(task.assignment_id)
            if not existing_assignment and not task.completed:
                session.delete(task)
                existing_tasks_by_id.pop(task_id)

    session.commit()

    return existing_tasks_by_id.values()

def commit_generated_tasks(
    new_tasks : TaskList,
    existing_tasks : list[Task],
    username : str,
    user : User,
    session : Session
) -> list[Task]:
    """
    Update an arbitrary user's list of assignment
    tasks to match a list of LLM-generated
    tasks. Creates all new tasks, updates
    existing tasks, and deletes task not
    in the list.

    Args:
        new_tasks (TaskList): List of LLM-generated tasks.
        existing_tasks (list[Task]): List of the user's existing tasks from the DB.
        username (str): Name of the user to update tasks for.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Raises:
        HTTPException: Raises a 404 if a non-adminstrator user attempts to update another user's task list.

    Returns:
        list[Task]: The user's updated list of tasks.
    """

    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")
    
    existing_user = session.exec(
        select(User)
        .where(User.username==username)
    ).first()

    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User not found: {username}")
    
    # existing_tasks : list[Task] = get_all_tasks_for_user(
    #     username=username,
    #     incomplete_only=True,
    #     offset=0,
    #     limit=100,
    #     user=user,
    #     session=session
    # )
    
    existing_tasks_by_id : dict[int, Task] = {task.id : task for task in existing_tasks if task.id is not None}

    header = {
        "created_at" : datetime.now(timezone.utc),
        "user_id" : existing_user.id,
        "completed": False,
        "in_progress": False
    }

    modified_tasks : list[Task] = []

    new_task_ids = [task.id for task in new_tasks.tasks if task.id is not None]

    for task in new_tasks.tasks:
        
        task_data = task.model_dump(exclude_unset=True)

        # If task does not exist, create it:
        if not task.id:

            # Do NOT allow the LLM to add completed tasks
            if task.completed:
                continue

            new_task = Task.model_validate(
                TaskCreate.model_validate(task_data),
                update=header
            )
            session.add(new_task)
            modified_tasks.append(new_task)
        
        # If task does exist, update it:
        else:
            existing_task = existing_tasks_by_id.get(task.id)
            if not existing_task:
                # raise HTTPException(status_code=404, detail=f"Task not found with ID {task.id}")
                warnings.warn(f"Task not found with ID {task.id}")
                continue
            
            # DO NOT allow the LLM to modify tasks which are completed
            if existing_task.completed:
                continue

            update = TaskUpdate.model_validate(
                task_data, update=header
            ).model_dump(exclude_unset=True)

            existing_task.sqlmodel_update(update)
            modified_tasks.append(existing_task)
    
    # Delete all user tasks which aren't in the new list
    for task_id, task in existing_tasks_by_id.items():

        # Do NOT allow the LLM to delete tasks which are completed
        if task_id not in new_task_ids and not task.completed:
            session.delete(task)

    session.commit()

    for task in modified_tasks:
        session.refresh(task)
    
    return modified_tasks

@router.get("/tasks_generate/self", response_model=TaskGenerationResult)
async def generate_tasks_for_self(
    commit : bool = True,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> TaskGenerationResult:
    """
    For the current student, use the LLM to create or update their list of assignment tasks.

    Args:
        commit (bool, optional): Whether to update the user's tasks list in the database to match the LLM-generated tasks. Defaults to True.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to the SQL database.

    Raises:
        HTTPException: Raises a 500 if the LLM fails in any way to generate the task list.

    Returns:
        TaskGenerationResult: The list of LLM generated task as well as the current list of user tasks in the database.
    """

    result = await generate_tasks_for_user(
        username=user.username,
        commit=commit,
        user=user,
        session=session
    )
    
    return result

@router.get("/tasks_generate/{username}", response_model=TaskGenerationResult)
async def generate_tasks_for_user(
    username : str,
    commit : bool = True,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> TaskGenerationResult:
    """
    For any given student, use the LLM to create or update their list of assignment tasks.

    Args:
        username (str): Name of the student to update assignment tasks for.
        commit (bool, optional): Whether to update the user's tasks list in the database to match the LLM-generated tasks. Defaults to True.
        user (User, optional): The currently logged in user.
        magic (str, optional): The user's magic. TODO: This should not be necessary.
        session (Session, optional): Connection to the SQL database.

    Raises:
        HTTPException: Raises a 401 if a non-administrator user attempts to generate new tasks for another user.
        HTTPException: Raises a 500 if the LLM fails in any way to generate the task list.

    Returns:
        TaskGenerationResult: The list of LLM generated task as well as the current list of user tasks in the database.
    """
    
    # Imported lazily to avoid circular import
    from ..llm_api import create_tasks_for_user

    if username != user.username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    # First, delete all tasks which no longer reference an assignment the user has.
    cleanup_tasks_for_user(
        username=username,
        user=user,
        session=session
    )

    try:
        gen_result = await create_tasks_for_user(
            username=username,
            user=user,
            session=session
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting LLM to generate tasks list for user: {str(e)}")

    new_tasks = gen_result.tasks

    existing_tasks : list[Task] = get_all_tasks_for_user(
        username=username,
        incomplete_only=False,
        offset=0,
        limit=100,
        user=user,
        session=session
    )

    if commit and not gen_result.llm_bypassed:
        existing_tasks = commit_generated_tasks(
            new_tasks=new_tasks,
            existing_tasks=existing_tasks,
            username=username,
            user=user,
            session=session
        )
        save_tasks_generation_assignments_snapshot(username=username, session=session)

    return TaskGenerationResult(
        generated_tasks = new_tasks.tasks,
        updated_tasks_list = existing_tasks
    )
