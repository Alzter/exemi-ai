from ..models import User
from ..models import University
from ..models import Term, TermPublic, TermPublicWithUnits
from ..models import Unit,  UnitPublic, UnitPublicWithAssignmentGroups
from ..models import AssignmentGroup, AssignmentGroupPublicWithUnit, AssignmentGroupPublicWithAssignments
from ..models import Assignment, AssignmentPublic, AssignmentPublicWithGroup
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_current_user

router = APIRouter()

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

@router.get("/terms", response_model=list[TermPublic])
async def get_terms(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    terms = session.exec(
        select(Term).offset(offset).limit(limit)
    ).all()
    return terms 

@router.get("/term/{id}", response_model=TermPublicWithUnits)
async def get_term(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    term = session.get(Term, id)
    if not term: raise HTTPException(status_code=404, detail="Term not found")
    return term

@router.get("/units", response_model=list[UnitPublic])
async def get_units(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    units = session.exec(
        select(Unit).offset(offset).limit(limit)
    ).all()
    return units

@router.get("/units/{id}", response_model=UnitPublicWithAssignmentGroups)
async def get_unit(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    unit = session.get(Unit, id)
    if not unit: raise HTTPException(status_code=404, detail="Unit not found")
    return unit

@router.get("/assignment_groups", response_model=list[AssignmentGroupPublicWithUnit])
async def get_assignment_groups(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    groups = session.exec(
        select(AssignmentGroup).offset(offset).limit(limit)
    ).all()
    return groups

@router.get("/assignment_groups/{id}", response_model=AssignmentGroupPublicWithAssignments)
async def get_assignment_group(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    group = session.get(AssignmentGroup, id)
    if not group: raise HTTPException(status_code=404, detail="Assignment group not found")
    return group

@router.get("/assignments", response_model=list[AssignmentPublicWithGroup])
async def get_assignments(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignments = session.exec(
        select(Assignment).offset(offset).limit(limit)
    ).all()
    return assignments

@router.get("/assignments/{id}", response_model=AssignmentPublicWithGroup)
async def get_assignment(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignment = session.get(Assignment, id)
    if not assignment: raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment 
