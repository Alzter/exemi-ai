from ..models import University, User
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic

router = APIRouter()

# TODO: This should be admin-only
@router.post("/university/", response_model=University)
async def create_university(university : University, current_user : User = Depends(get_current_user), session : Session = Depends(get_session)):
    if not current_user.admin: raise HTTPException(status_code=401, detail="Only administrators may create universities")
    session.add(university)
    session.commit()
    session.refresh(university)
    return university

@router.get("/university/", response_model=list[University])
async def get_universities(session : Session = Depends(get_session)):
    return session.exec(select(University)).all()
