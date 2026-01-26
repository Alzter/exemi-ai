from ..models import User, UserCreate, UserUpdate, UserPublic, Token
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas
from pandas import DataFrame

router = APIRouter()

@router.get("/assignments/")
async def get_assignments(current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):

    units = await query_canvas(path="courses", magic=magic, provider = current_user.magic_provider, max_items=50)
    
    return units
