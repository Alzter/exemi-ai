from ..models import User, UserPublic, Reminder, ReminderPublic, ReminderCreate, ReminderUpdate
from typing import Annotated, Literal
from sqlmodel import Session, select, desc
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from ..dependencies import get_session
from ..dependencies import get_current_user
from datetime import datetime, timedelta, timezone
router = APIRouter()

@router.get("/reminders", response_model=list[ReminderPublic])
def get_reminders(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a list of the current user's reminders.
 
     Args:
         offset (int): Pagination start index.
         limit (int): Page length. Maximum of 100.
 
     Returns:
         List[ReminderPublic]: The reminders.
    """
    reminders = session.exec(
        select(Reminder)
        .order_by(Reminder.due_at)
        .join(User).where(User.username == user.username)
        .offset(offset).limit(limit)
    ).all()

    return reminders

@router.get("/reminder/{id}", response_model=ReminderPublic)
def get_reminder(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain an existing reminder.

    Args:
        id (int): The ID of the reminder.
    
    Raises:
        HTTPException:
            If the current user is not an administrator, this will return a 401 (Unauthorized) response when attempting to view other users' reminders.
            This will also return a 404 (not found) if the reminder did not exist in the DB.
    
    Returns:
        ReminderPublic: The reminder.
    """
    reminder = session.get(Reminder, id)

    if not reminder: raise HTTPException(status_code=404, detail=f"Reminder not found with ID {id}")

    if not reminder.user_id == user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to view this reminder")

    return reminder

@router.post("/reminder", response_model=ReminderPublic)
def create_reminder(
    data : ReminderCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new reminder for the current user.

    Args:
        data (ReminderCreate): The reminder's due date, description, and Canvas assignment ID.
    
    Raises:
        HTTPException: Raises a 400 if you try to create more than one reminder for the same Canvas assignment.

    Returns:
        ReminderPublic: The reminder.
    """

    # reminders_for_the_same_assignment = session.exec(
    #     select(Reminder).where(Reminder.user_id == user.id).where(Reminder.canvas_assignment_id == data.canvas_assignment_id)
    # ).all()

    # if reminders_for_the_same_assignment:
    #     raise HTTPException(status_code=400, detail="You cannot have more than one reminder for the same assignment!")

    reminder = Reminder.model_validate(data, update={
        "user_id" : user.id,
        "created_at" : datetime.now(timezone.utc)
    })

    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder

@router.delete("/reminder/{id}", response_model=Literal[True])
def delete_reminder(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Deletes a reminder for a given user.

    Args:
        id (int): The ID of the reminder to delete.

    Raises:
        HTTPException: Returns a 401 if the user tries to delete another user's reminder and is not an administrator.
    
    Returns:
        Literal[True]: Successful response.
    """
    reminder = session.get(Reminder, id)
    if not reminder: raise HTTPException(status_code=404, detail="Reminder not found")

    if reminder.user_id != user.id and not user.admin: raise HTTPException(status_code=401, detail="You are not authorised to delete this reminder")
    session.delete(reminder)
    session.commit()
    return True

@router.patch("/reminder/{id}", response_model=ReminderPublic)
def update_reminder(
    id : int,
    new_data : ReminderUpdate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Change the details of a reminder for a given user. 
    
    Args:
        id (int): The ID of the reminder to modify.
        new_data (ReminderUpdate): Changes to the reminder's description, due date, or Canvas assignment ID.
    
    Raises:
        HTTPException: Raises a 400 if you try to create more than one reminder for the same Canvas assignment.

    Returns:
        ReminderPublic: The updated reminder.
    """
    reminder = session.get(Reminder, id)
    if not reminder: raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder.user_id != user.id and not user.admin: raise HTTPException(status_code=401, detail="You are not authorised to edit another user's reminder")
    
    # reminders_for_the_same_assignment = session.exec(
    #     select(Reminder).where(Reminder.user_id == reminder.user.id).where(Reminder.canvas_assignment_id == new_data.canvas_assignment_id)
    # ).all()

    # if reminders_for_the_same_assignment:
    #     raise HTTPException(status_code=400, detail="You cannot have more than one reminder for the same assignment!")

    new_data_dict = new_data.model_dump(exclude_unset=True)
    reminder.sqlmodel_update(new_data_dict)

    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder
