from ..models import User, Assignment
from ..models import Task, TaskCreate, TaskUpdate, TaskPublic
from typing import Literal
from sqlmodel import Session, select
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session
from ..dependencies import get_current_user
from ..date_utils import parse_timestamp
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

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
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> list[Task]:
    """
    Obtain all incomplete and complete tasks for the current user.

    Args:
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        list[Task]: The list of tasks.
    """
    return get_all_tasks_for_user(
        username=user.username,
        offset=offset,
        limit=limit,
        user=user,
        session=session,
    )

@router.get("/tasks_all/{username}", response_model=list[TaskPublic])
def get_all_tasks_for_user(
    username : str,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> list[Task]:
    """
    Obtain all incomplete and complete tasks for an arbitrary user.

    Args:
        username (str): Which user to obtain task list for.
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Maximum number of tasks to obtain. Defaults to 100. Max of 100.
        user (User, optional): The currently logged in user.
        session (Session, optional): Connection to SQL database.

    Returns:
        list[Task]: The list of tasks.
    """
    if user.username != username and not user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")
    
    tasks = session.exec(
        select(Task)
        .join(User)
        .where(User.username==username)
        .order_by(Task.due_at)
        .offset(offset)
        .limit(limit)
    )

    return tasks

@router.get("/tasks/self", response_model=list[TaskPublic])
def get_tasks_for_self(
    date: datetime = datetime.now(timezone.utc),
    current_date: datetime = datetime.now(timezone.utc),
    timezone_name: str = "Australia/Sydney",
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

    Returns:
        Task: The new task.
    """
    existing_user = user

    if user.username != username:
        if not user.admin:
            raise HTTPException(status_code=401, detail="Unauthorised")

        existing_user = session.exec(
            select(User).where(User.username == username)
        ).first()

        if not existing_user:
            raise HTTPException(status_code=404, detail=f"User not found: {username}")

    if data.assignment_id is not None:
        existing_assignment = session.get(Assignment, data.assignment_id)
        if not existing_assignment:
            raise HTTPException(
                status_code=400,
                detail=f"Assignment not found with ID {data.assignment_id}",
            )

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

    Returns:
        Task: The new task.
    """
    return create_task_for_user(
        username=user.username,
        data=data,
        user=user,
        session=session,
    )


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

    Returns:
        Task: The updated task.
    """
    task = get_task(id=id, user=user, session=session)

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
