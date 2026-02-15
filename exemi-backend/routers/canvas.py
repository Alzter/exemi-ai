from pydantic import TypeAdapter
from ..models import User, UserCreate, UserUpdate, UserPublic
# from ..models import University, UniversityCreate, UniversityPublic
from ..models import Term, TermCreate, TermPublic
from ..models import Unit, UnitCreate, UnitPublic
from ..models import Assignment, AssignmentCreate, AssignmentPublic
from ..models_canvas import CanvasTerm, CanvasUnit, CanvasAssignment, CanvasAssignmentGroup
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas

router = APIRouter()

canvas_terms_adapter = TypeAdapter(list[CanvasTerm])
canvas_units_adapter = TypeAdapter(list[CanvasUnit])
canvas_assignment_group_adapter = TypeAdapter(list[CanvasAssignmentGroup])

@router.get("/canvas/terms", response_model=list[CanvasTerm])
async def canvas_get_terms(
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    units = await canvas_get_units(user=user, magic=magic, exclude_complete_units=False, exclude_organisation_units=False)
    
    # Obtain every term object from every unit the user is currently enrolled in.
    raw_terms = [unit.term for unit in units]
    
    # Remove all duplicates and sort by ID.
    terms = sorted(
        {term.id: term for term in raw_terms}.values(),
        key=lambda term: term.id
    )

    return terms

# @router.post("/canvas/terms", response_model=list[TermPublic])
# async def create_terms_from_canvas(
#     session: Session = Depends(get_session),
#     user: User = Depends(get_current_user),
#     magic: str = Depends(get_current_magic)
# ):
#     """
#     Creates Term objects in the database to represent
#     all the Terms that the student has access to from
#     Canvas.
#     """
# 
#     db_terms: list[Term] = []
#     new_terms: list[Term] = []
# 
#     # Get terms from Canvas
#     canvas_terms: list[CanvasTerm] = await canvas_get_terms(user=user, magic=magic)
# 
#     for term in canvas_terms:
#         # Check if term already exists
#         existing_term = session.exec(
#             select(Term)
#             .where(Term.canvas_id == term.id)
#             .where(Term.university_name == user.university_name)
#         ).first()
# 
#         if existing_term:
#             db_terms.append(existing_term)
#         else:
#             new_terms.append(term)
# 
#     # Add all new terms at once
#     session.add_all(new_terms)
#     session.commit()
# 
#     # Refresh new terms so IDs are populated
#     for term in new_terms:
#         session.refresh(term)
# 
#     # Combine existing and newly added terms
#     db_terms.extend(new_terms)
# 
#     return db_terms

@router.get("/canvas/units", response_model=list[CanvasUnit])
async def canvas_get_units(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    params = {"include":"term"}
    if exclude_complete_units: params["enrollment_state"] = "active"
    raw_units = await query_canvas(path="courses", magic=magic, provider=user.university_name, max_items=50, params=params)
    
    # return raw_units
    units = canvas_units_adapter.validate_json(raw_units)
    
    # Internally, Swinburne Organisation units have term ID 1
    # ("Default Term"), so we can exclude them with this check:
    if exclude_organisation_units:
        units = [unit for unit in units if unit.enrollment_term_id != 1]

    return units
     
# @router.post("/canvas/units", response_model=list[UnitPublic])
# async def create_units_from_canvas(
#     session : Session = Depends(get_session),
#     user : User = Depends(get_current_user),
#     magic : str = Depends(get_current_magic)
# ):
#     """
#     Creates Unit objects in the database to represent
#     all the Units that the student has access to from
#     Canvas.
# 
#     Preconditions:
#     -   You must call POST /canvas/terms first. 
#     """
#     new_units = []
#     db_units = []
# 
#     canvas_units : list[Unit] = await canvas_get_units(user=user, magic=magic)
# 
#     for unit in canvas_units:
#         
#         # Obtain the Term object from the DB which contains the unit.
#         existing_term = session.exec(
#             select(Term).where(
#                 Term.canvas_id==unit.canvas_term_id
#             ).where(
#                 Term.university_name==user.university_name
#             )
#         ).first()
#         
#         # If there is no Term in the DB to contain the unit, vomit
#         if not existing_term: raise HTTPException(
#             status_code=404,
#             detail=f"Cannot create unit {unit.name} because its term does not exist in the database. Run POST /canvas_terms first!!"
#         )
#         
#         existing_unit = session.exec(
#             select(Unit).join(Term).where(
#                 Unit.canvas_id==unit.canvas_id
#             ).where(
#                 Term.university_name==user.university_name
#             )
#         ).first()
# 
#         if existing_unit:
#             db_units.append(existing_unit)
#             continue
#         
#         unit.term_id = existing_term.id
#         new_units.append(unit)
#     
#     session.add_all(new_units)
#     session.commit()
# 
#     # TODO: Enrol the user in all active units
#     # by adding entries in the UsersUnits table! FIXME
# 
#     for unit in new_units:
#         unit = session.refresh(unit)
#     
#     db_units.extend(new_units)
#     return db_units
# 
# # @router.get("/canvas/units/{unit_id}/term", response_model=TermPublic)
# # async def canvas_get_term(unit_id : int, user : User = Depends(get_current_user), magic : str = Depends(get_current_magic)):
# #     
# #     # TODO: Terms provide a start_at and end_at date.
# #     # HOWEVER, the dates provided by SUT are often inaccurate!!
# #     # Find a way to CROSS REFERENCE the term start and end dates
# #     # using the name of the term (e.g., "Semester 1 2024")
# #     # through Swinburne's official timetable!! FIXME
# # 
# #     params = {"include":"term"}
# #     unit_data = await query_canvas(path=f"courses/{unit_id}", magic=magic, provider=user.university_name, max_items=50, params=params)
# #     term_df = decode_canvas_response( unit_data.term.to_list() )
# #     term_data = term_df.to_dict(orient='records')[0]
# #     
# #     return Term.model_validate(term_data)
 
@router.get("/canvas/units/{unit_id}/assignment_groups", response_model = list[CanvasAssignmentGroup])
async def canvas_get_assignment_groups(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":"assignments"}

    raw_assignment_groups = await query_canvas(path=path, magic=magic, provider=user.university_name, max_items=50, params=params)
    
    assignment_groups = canvas_assignment_group_adapter.validate_json(raw_assignment_groups)
    return assignment_groups

@router.get("/canvas/units/{unit_id}/assignments", response_model=list[CanvasAssignment])
async def canvas_get_assignments(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    assignment_groups = await canvas_get_assignment_groups(unit_id=unit_id, user=user, magic=magic)
    
    # TODO: Add a field to each assignment which represents its contribution to the unit's points.
    assignments = []
    for group in assignment_groups:
        assignments.extend(group.assignments)

    return assignments

@router.get("/canvas/assignment_groups", response_model = list[CanvasAssignmentGroup])
async def canvas_get_all_assignment_groups(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    units : list[CanvasUnit] = await canvas_get_units(
        exclude_complete_units=exclude_complete_units,
        exclude_organisation_units=exclude_organisation_units,
        user=user, magic=magic)
    
    groups = []
    for unit in units:
        unit_assignment_groups = await canvas_get_assignment_groups(unit_id=unit.id, user=user, magic=magic)
        groups.extend(unit_assignment_groups)
    
    return groups

@router.get("/canvas/assignments", response_model = list[CanvasAssignment])
async def canvas_get_all_assignments(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    units : list[CanvasUnit] = await canvas_get_units(
        exclude_complete_units=exclude_complete_units,
        exclude_organisation_units=exclude_organisation_units,
        user=user, magic=magic)
    
    assignments = []
    for unit in units:
        unit_assignments = await canvas_get_assignments(unit_id=unit.id, user=user, magic=magic)
        assignments.extend(unit_assignments)
    
    return assignments

