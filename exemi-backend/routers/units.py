from ..models import User, UserCreate, UserUpdate, UserPublic
# from ..models import University, UniversityCreate, UniversityPublic
from ..models import Term, TermCreate, TermPublic
from ..models import Unit, UnitCreate, UnitPublic
from ..models import Assignment, AssignmentCreate, AssignmentPublic
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas, decode_canvas_response
from fastapi.responses import JSONResponse
import pandas as pd

router = APIRouter()

# def pandas_get(column, row, dtype):
#     cell = column.get(row)
#     if pd.isna(cell): return None

def parse_pandas_datetime(cell):
    """
    There is a bug converting Pandas datetime columns
    into SQLModel datetime | None columns. When a Pandas datetime
    column has an empty value, it is represented as a NAT (not a time)
    object. However, when SQLModel attempts to parse NAT, instead
    of converting it to NULL in the DB, it raises the exception:
    "TypeError: 'float' object cannot be interpreted as an integer."
    To circumvent this, we must manually convert NAT to None
    so that SQLModel properly converts it to NULL in the database.
    """
    if pd.isna(cell): return None
    return cell

@router.get("/canvas/terms", response_model=list[Term])
async def canvas_get_terms(current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {"include":"term"}
    raw_units = await query_canvas(path="courses", magic=magic, provider=current_user.university_name, max_items=50, params=params)

    raw_terms = decode_canvas_response(raw_units["term"].to_list())
    raw_terms = raw_terms.drop_duplicates(subset="id").dropna()
    
    terms = []

    for term in raw_terms.to_dict(orient='records'):
        term_data = {
            "canvas_id" : term.get("id"),
            "name" : term.get("name"),
            "university_name" : current_user.university_name,
            "start_at" : parse_pandas_datetime(term.get("start_at")),
            "end_at" : parse_pandas_datetime(term.get("end_at"))
        }

        term_model = Term.model_validate(term_data)
        terms.append(term_model)
    
    return terms

@router.post("/canvas/terms", response_model=list[TermPublic])
async def create_terms_from_canvas(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    magic: str = Depends(get_current_magic)
):
    """
    Creates Term objects in the database to represent
    all the Terms that the student has access to from
    Canvas.
    """

    db_terms: list[Term] = []
    new_terms: list[Term] = []

    # Get terms from Canvas
    canvas_terms: list[Term] = await canvas_get_terms(current_user=current_user, magic=magic)

    for term in canvas_terms:
        # Check if term already exists
        existing_term = session.exec(
            select(Term)
            .where(Term.canvas_id == term.canvas_id)
            .where(Term.university_name == term.university_name)
        ).first()

        if existing_term:
            db_terms.append(existing_term)
        else:
            new_terms.append(term)

    # Add all new terms at once
    session.add_all(new_terms)
    session.commit()

    # Refresh new terms so IDs are populated
    for term in new_terms:
        session.refresh(term)

    # Combine existing and newly added terms
    db_terms.extend(new_terms)

    return db_terms

@router.get("/canvas/units", response_model=list[Unit])
async def canvas_get_units(exclude_complete_units : bool = False, exclude_orginisation_units : bool = True, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    params = {"include":"term"}
    if exclude_complete_units: params["enrollment_state"] = "active"
    
    raw_units = await query_canvas(path="courses", magic=magic, provider=current_user.university_name, max_items=50, params=params)
    
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
            "canvas_id" : unit.get("id"),
            "name" : unit_name,
            "assignments" : [],
            "canvas_term_id" : term_dict.get("id")
        }

        unit_model = Unit.model_validate(unit_data)
        units.append(unit_model)
    
    return units

@router.post("/canvas/units", response_model=list[UnitPublic])
async def create_units_from_canvas(
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    """
    Creates Unit objects in the database to represent
    all the Units that the student has access to from
    Canvas.

    Preconditions:
    -   You must call POST /canvas/terms first. 
    """
    new_units = []
    db_units = []

    canvas_units : list[Unit] = await canvas_get_units(current_user=current_user, magic=magic)

    for unit in canvas_units:
        
        # Obtain the Term object from the DB which contains the unit.
        existing_term = session.exec(
            select(Term).where(
                Term.canvas_id==unit.canvas_term_id
            ).where(
                Term.university_name==current_user.university_name
            )
        ).first()
        
        # If there is no Term in the DB to contain the unit, vomit
        if not existing_term: raise HTTPException(
            status_code=404,
            detail=f"Cannot create unit {unit.name} because its term does not exist in the database. Run POST /canvas_terms first!!"
        )
        
        existing_unit = session.exec(
            select(Unit).join(Term).where(
                Unit.canvas_id==unit.canvas_id
            ).where(
                Term.university_name==current_user.university_name
            )
        ).first()

        if existing_unit:
            db_units.append(existing_unit)
            continue
        
        unit.term_id = existing_term.id
        new_units.append(unit)
    
    session.add_all(new_units)
    session.commit()

    # TODO: Enrol the user in all active units
    # by adding entries in the UsersUnits table! FIXME

    for unit in new_units:
        unit = session.refresh(unit)
    
    db_units.extend(new_units)
    return db_units

# @router.get("/canvas/units/{unit_id}/term", response_model=TermPublic)
# async def canvas_get_term(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
#     
#     # TODO: Terms provide a start_at and end_at date.
#     # HOWEVER, the dates provided by SUT are often inaccurate!!
#     # Find a way to CROSS REFERENCE the term start and end dates
#     # using the name of the term (e.g., "Semester 1 2024")
#     # through Swinburne's official timetable!! FIXME
# 
#     params = {"include":"term"}
#     unit_data = await query_canvas(path=f"courses/{unit_id}", magic=magic, provider=current_user.university_name, max_items=50, params=params)
#     term_df = decode_canvas_response( unit_data.term.to_list() )
#     term_data = term_df.to_dict(orient='records')[0]
#     
#     return Term.model_validate(term_data)

@router.get("/canvas/units/{unit_id}/assignments", response_model = list[Assignment])
async def canvas_get_assignments(unit_id : int, current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":"assignments"}

    assignment_groups = await query_canvas(path=path, magic=magic, provider=current_user.university_name, max_items=50, params=params)
    assignment_groups["course_id"] = unit_id

    raw_assignments = assignment_groups.assignments.explode().dropna().tolist()
    raw_assignments = decode_canvas_response(raw_assignments)

    assignments = []
    for assignment in raw_assignments.to_dict(orient='records'):
        description = assignment.get("description")
        if type(description) is not str: description = ""
        
        assignment_data = {
            "canvas_id" : assignment.get("id"),
            "name" : assignment.get("name"),
            "description" : description,
            "due_at":parse_pandas_datetime(assignment.get("datetime")),
            "is_group":False, # TODO: FIX
            "points":0, # TODO: FIX
            "unit_id":unit_id
        }

        try:
            assignment_model = Assignment.model_validate(assignment_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error {assignment.get("id")} {str(e)}")
        assignments.append(assignment_model)
    
    return assignments

@router.get("/canvas/assignments", response_model = list[Assignment])
async def canvas_get_all_assignments(
    current_user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    units : list[Unit] = await canvas_get_units(current_user=current_user,magic=magic)
    
    assignments : list[Assignment] = []

    for unit in units:
        unit_assignments : list[Assignment] = await canvas_get_assignments(
            unit.canvas_id,
            current_user=current_user,
            magic=magic
        )

        assignments.extend(unit_assignments)
    
    return assignments

# @router.get("/universities", response_model=list[UniversityPublic])
# async def get_universities(session : Session = Depends(get_session)):
#     universities = session.exec(select(University)).all()
#     return universities
# 
# @router.post("/universities", response_model=UniversityPublicWithUnits)
# async def create_university(data : UniversityCreate, session : Session = Depends(get_session)):
#     university = University.model_validate(data)
#     session.add(university)
#     session.commit()
#     session.refresh(university)
#     return university

@router.get("/terms", response_model=list[TermPublic])
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

@router.post("/term", response_model=TermPublic)
async def create_term(data : TermCreate, session : Session = Depends(get_session)):
    term = Term.model_validate(data)
    session.add(term)
    session.commit()
    session.refresh(term)
    return term

@router.get("/units", response_model=list[UnitPublic])
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

@router.post("/unit", response_model=UnitPublic)
async def create_unit(data : UnitCreate, session : Session = Depends(get_session)):
    unit = Unit.model_validate(data)
    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit

@router.get("/assignments", response_model=list[AssignmentPublic])
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

@router.post("/assignment", response_model=AssignmentPublic)
async def create_assignment(data : AssignmentCreate, session : Session = Depends(get_session)):
    assignment = Assignment.model_validate(data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment

# @router.post("/canvas/units", response_model = list[UnitPublic])
# async def create_units_from_canvas(session : Session = Depends(get_session), current_user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
#     """
#     For a given Canvas user, creates Unit objects in the database for all their units
#     and recursively creates University, Term, and Assignment objects to populate the fields.
#     """
#     
#     university_name : str = current_user.university_name
#     
#     # TODO: Create a University object if one does not exist!
# 
#     # existing_university : University = session.exec(select(University, university_name))
# 
#     units : list[UnitPublic] = await canvas_get_units(current_user=current_user,magic=magic)
#     
#     new_units = []
#     for unit_data in units:
#         
#         # If unit already exists, do not create it!
#         existing_unit = session.exec(
#             select(Unit).where(Unit.name == unit_data.name)
#         ).first()
#         if existing_unit:
#             continue
#         
#         term_data : Term = await canvas_get_term(unit_data.id, current_user=current_user,magic=magic)
#         
#         # If the unit's term does not exist, create it in the database
#         existing_term = session.exec(select(Term).where(Term.name == term_data.name)).first()
#         if not existing_term:
#             term = TermCreate.model_validate(term_data.model_dump())
#             existing_term = await create_term(term, session)
# 
#         # Create the unit
#         unit = UnitCreate.model_validate(unit_data.model_dump(), update={
#             "term_id" : existing_term.id
#         })
# 
#         existing_unit = await create_unit(unit, session)
#         
#         # TODO: Create assignments for the unit!
# 
#         new_units.append(existing_unit)
# 
#         # # If the unit's term does NOT exist, create it!
#         # existing_term = session.exec(select(Term, unit.term_id)).first()
#         # if not existing_term:
#         #     term_data : Term = await canvas_get_term(unit.id, current_user=current_user,magic=magic)
#         #     existing_term = await create_term(term_data, session=session)
#         # 
#         # # Create the unit!
#         # db_unit = create_unit(unit, session=session)
# 
#         # assignments : list[AssignmentPublic] = await canvas_get_assignments(unit.id, current_user=current_user,magic=magic)
#         # for assignment in assignments:
#         #     await create_assignment(assignment, session=session)
# 
#         # # Update the Unit to have the assignments and term information.
#         # unit = unit.copy()
#         # #unit.assignments = assignments
#         # unit.term_id = existing_term.id
#         # new_units.append(unit)
# 
# 
#     return new_units
