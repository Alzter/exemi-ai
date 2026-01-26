from ..models import User, UserCreate, UserUpdate, UserPublic, Unit, UnitPublic, Term, TermPublic, Assignment, AssignmentPublic
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas, decode_canvas_response
from fastapi.responses import JSONResponse
import pandas as pd

router = APIRouter()

@router.get("/units/", response_model=list[UnitPublic])
async def canvas_get_units(exclude_complete_units : bool = False, exclude_orginisation_units : bool = True, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {}#"include":"term"}
    if exclude_complete_units: params["enrollment_state"] = "active"
    
    raw_units = await query_canvas(path="courses", magic=magic, provider=current_user.magic_provider, max_items=50, params=params)
    
    # Internally, Swinburne Organisation (ORG) units are assigned to enrollment term ID 1
    # Since we're only concerned with academic units, let's filter out organisation units
    if exclude_orginisation_units:
        raw_units = raw_units.loc[raw_units.enrollment_term_id != 1]

    units = []

    for unit in raw_units.to_dict(orient='records'):
        unit_name = unit.get("original_name")
        if type(unit_name) is not str: unit_name = unit.get("name")
        
        unit_data : list[Unit] = {
            "id" : unit.get("id"),
            "name" : unit_name,
            "assignments" : []
        }

        unit_model = Unit.model_validate(unit_data)
        units.append(unit_model)
    
    return units

@router.get("/units/{unit_id}/term/", response_model=TermPublic)
async def canvas_get_term(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {"include":"term"}
    unit_data = await query_canvas(path=f"courses/{unit_id}", magic=magic, provider=current_user.magic_provider, max_items=50, params=params)
    term_df = decode_canvas_response( unit_data.term.to_list() )
    term_data = term_df.to_dict(orient='records')[0]
    
    return Term.model_validate(term_data)


@router.get("/units/{unit_id}/assignments/", response_model = list[AssignmentPublic])
async def canvas_get_assignments(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":"assignments"}

    assignment_groups = await query_canvas(path=path, magic=magic, provider=current_user.magic_provider, max_items=50, params=params)
    assignment_groups["course_id"] = unit_id

    raw_assignments = assignment_groups.assignments.explode().dropna().tolist()
    raw_assignments = decode_canvas_response(raw_assignments)

    assignments : list[Assignment] = []
    for assignment in raw_assignments.to_dict(orient='records'):
        assignment_data = {
            "id" : assignment.get("id"),
            "name" : assignment.get("name"),
            "description" : assignment.get("description"),
            "due_at" : assignment.get("due_at"),
            "is_group" : False, # TODO: FIX
            "points" : 0, # TODO: FIX
        }
        assignment_model = Assignment.model_validate(assignment_data)
        assignments.append(assignment_model)
    
    return assignments
