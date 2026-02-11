from ..models import University, User
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic

router = APIRouter()

@router.post("/university", response_model=University)
async def create_university(
    university : University,
    current_user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new University object (ADMIN ONLY).

    Args:
        university (University): The name of the university wrapped in a University class.
    
    Raises:
        HTTPException: Raises a 401 if the current user is not an admin.

    Returns:
        University: The university object.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Only administrators may create universities")
    session.add(university)
    session.commit()
    session.refresh(university)
    return university

@router.get("/university", response_model=list[University])
async def get_universities(
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user)
):
    """
    Obtain all universities (ADMIN ONLY).

    Returns:
        List[University]: The universities.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    return session.exec(select(University)).all()
