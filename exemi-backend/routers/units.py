from ..models import User, UserCreate, UserUpdate, UserPublic, Token
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas
from fastapi.responses import JSONResponse
import pandas as pd

router = APIRouter()

@router.get("/units/")
async def get_units(exclude_complete_units : bool = False, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {}
    if exclude_complete_units: params["enrollment_state"] = "active"
    
    units = await query_canvas(path="courses", magic=magic, provider = current_user.magic_provider, max_items=50, params=params)
    return units.fillna(value="").to_dict(orient='records')

