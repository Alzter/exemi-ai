from ..models import User, UserCreate, UserUpdate, UserPublic, Unit, UnitCreate, UnitPublic, Term, TermCreate, TermPublic, Assignment, AssignmentPublic
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas, decode_canvas_response
from fastapi.responses import JSONResponse
import pandas as pd

router = APIRouter()

@router.get("/canvas/units", response_model=list[UnitPublic])
async def canvas_get_units(exclude_complete_units : bool = False, exclude_orginisation_units : bool = True, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {"include":"term"}
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

        term_dict = unit.get("term")
        if not term_dict: raise HTTPException(500, f"Unit {unit_name} does not have a term attached")

        unit_data = {
            "id" : unit.get("id"),
            "name" : unit_name,
            "assignments" : [],
            "term_id" : term_dict.get("id")
        }

        unit_model = Unit.model_validate(unit_data)
        units.append(unit_model)
    
    return units

@router.get("/canvas/units/{unit_id}/term/", response_model=TermPublic)
async def canvas_get_term(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    
    # TODO: Terms provide a start_at and end_at date.
    # HOWEVER, the dates provided by SUT are often inaccurate!!
    # Find a way to CROSS REFERENCE the term start and end dates
    # using the name of the term (e.g., "Semester 1 2024")
    # through Swinburne's official timetable!! FIXME

    params = {"include":"term"}
    unit_data = await query_canvas(path=f"courses/{unit_id}", magic=magic, provider=current_user.magic_provider, max_items=50, params=params)
    term_df = decode_canvas_response( unit_data.term.to_list() )
    term_data = term_df.to_dict(orient='records')[0]
    
    return Term.model_validate(term_data)

@router.get("/canvas/units/{unit_id}/assignments/", response_model = list[AssignmentPublic])
async def canvas_get_assignments(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":"assignments"}

    assignment_groups = await query_canvas(path=path, magic=magic, provider=current_user.magic_provider, max_items=50, params=params)
    assignment_groups["course_id"] = unit_id

    raw_assignments = assignment_groups.assignments.explode().dropna().tolist()
    raw_assignments = decode_canvas_response(raw_assignments)

    assignments = []
    for assignment in raw_assignments.to_dict(orient='records'):
        assignment_data = {
            "id" : assignment.get("id"),
            "name" : assignment.get("name"),
            "description" : assignment.get("description"),
            "due_at" : assignment.get("due_at"),
            "is_group" : False, # TODO: FIX
            "points" : 0, # TODO: FIX
            "unit_id" : unit_id
        }
        assignment_model = Assignment.model_validate(assignment_data)
        assignments.append(assignment_model)
    
    return assignments

@router.get("/terms/", response_model=list[TermPublic])
async def get_terms(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    terms = session.exec(
        select(Term).offset(offset).limit(limit)
    ).all()
    return terms 

@router.get("/term/{name}", response_model=TermPublic)
async def get_term(name : str, session : Session = Depends(get_session)):
    term = session.exec(
        select(Term).where(Term.name == name)
    ).first()
    if not term: raise HTTPException(status_code=404, detail="Term not found")
    return term

@router.post("/term/", response_model=TermPublic)
async def create_term(data : TermCreate, session : Session = Depends(get_session)):
    term = Term.model_validate(data)
    session.add(term)
    session.commit()
    session.refresh(term)
    return term

@router.get("/units/", response_model=list[UnitPublic])
async def get_units(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    units = session.exec(
        select(Unit).offset(offset).limit(limit)
    ).all()
    return units

@router.get("/units/{name}", response_model=UnitPublic)
async def get_unit(name : str, session : Session = Depends(get_session)):
    unit = session.exec(
        select(Term).where(Unit.name == name)
    ).first()
    if not unit: raise HTTPException(status_code=404, detail="Unit not found")
    return unit 

@router.post("/unit/", response_model=UnitPublic)
async def create_unit(data : UnitCreate, session : Session = Depends(get_session)):
    unit = Unit.model_validate(data)
    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit

@router.get("/assignments/", response_model=list[UnitPublic])
async def get_assignments(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    assignments = session.exec(
        select(Assignment).offset(offset).limit(limit)
    ).all()
    return assignments

@router.get("/units/{name}", response_model=UnitPublic)
async def get_assignment(name : str, session : Session = Depends(get_session)):
    assignment = session.exec(
        select(Assignment).where(Assignment.name == name)
    ).first()
    if not assignment: raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment 

@router.post("/assignment/", response_model=AssignmentPublic)
async def create_assignment(data : Assignment, session : Session = Depends(get_session)):
    assignment = Assignment.model_validate(data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment

@router.post("/units/", response_model = list[UnitPublic])
async def create_units(session : Session = Depends(get_session), current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    """
    For a given Canvas user, creates Unit objects in the database for all their units
    and recursively creates University, Term, and Assignment objects to populate the fields.
    """

    units : list[UnitPublic] = await canvas_get_units(current_user=current_user,magic=magic)
    
    new_units = []
    for unit in units:
        
        try:
            # If unit already exists, do not create it!
            existing_unit = session.exec(
                select(Unit).where(Unit.name == unit.name)
            ).first()
            if existing_unit: continue
            
            term_data = canvas_get_term(unit.id, current_user=current_user,magic=magic)
            

            # # If the unit's term does NOT exist, create it!
            # existing_term = session.exec(select(Term, unit.term_id)).first()
            # if not existing_term:
            #     term_data : Term = await canvas_get_term(unit.id, current_user=current_user,magic=magic)
            #     existing_term = await create_term(term_data, session=session)
            # 
            # # Create the unit!
            # db_unit = create_unit(unit, session=session)

            # assignments : list[AssignmentPublic] = await canvas_get_assignments(unit.id, current_user=current_user,magic=magic)
            # for assignment in assignments:
            #     await create_assignment(assignment, session=session)

            # # Update the Unit to have the assignments and term information.
            # unit = unit.copy()
            # #unit.assignments = assignments
            # unit.term_id = existing_term.id
            # new_units.append(unit)

        except: pass

    return new_units
