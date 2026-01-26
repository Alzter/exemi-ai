from ..models import User, UserCreate, UserUpdate, UserPublic, Unit, UnitPublic
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas
from fastapi.responses import JSONResponse
import pandas as pd

router = APIRouter()

@router.get("/units/", response_model=list[UnitPublic])
async def get_units(exclude_complete_units : bool = False, exclude_orginisation_units : bool = True, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {}
    if exclude_complete_units: params["enrollment_state"] = "active"
    
    raw_units = await query_canvas(path="courses", magic=magic, provider = current_user.magic_provider, max_items=50, params=params)
    
    # Internally, Swinburne Organisation (ORG) units are assigned to enrollment term ID 1
    # Since we're only concerned with academic units, let's filter out organisation units
    if exclude_orginisation_units:
        raw_units = raw_units.loc[raw_units.enrollment_term_id != 1]

    units = []

    for unit in raw_units.to_dict(orient='records'):
        unit_name = unit.get("original_name")
        if type(unit_name) is not str: unit_name = unit.get("name")
    
        unit_data = {
            "id" : unit.get("id"),
            "name" : unit_name,
            "assignments" : []
        }

        unit_model = Unit.model_validate(unit_data)
        units.append(unit_model)
    
    return units

    
    
