from ..models import User, UserPublicWithUnits
from ..models import University
from ..models import Term, TermPublic, TermPublicWithUnits
from ..models import Unit,  UnitPublic, UnitPublicWithAssignmentGroups
from ..models import AssignmentGroup, AssignmentGroupPublicWithUnit, AssignmentGroupPublicWithAssignments
from ..models import Assignment, AssignmentPublic, AssignmentPublicWithGroup, UsersAssignments
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_current_user
from datetime import datetime, timezone

router = APIRouter()

@router.get("/university", response_model=list[University])
def get_universities(
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
def get_terms(
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
def get_term(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    term = session.get(Term, id)
    if not term: raise HTTPException(status_code=404, detail="Term not found")
    return term

@router.get("/units", response_model=list[UnitPublic])
def get_units(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    user_with_units = UserPublicWithUnits.model_validate(user)
    return user_with_units.units
    return units

@router.get("/units/{id}", response_model=UnitPublicWithAssignmentGroups)
def get_unit(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    unit = session.get(Unit, id)
    if not unit: raise HTTPException(status_code=404, detail="Unit not found")
    return unit

@router.get("/assignment_groups", response_model=list[AssignmentGroupPublicWithUnit])
def get_assignment_groups(
    date : datetime = datetime.now(timezone.utc),
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    user_units = get_units(user=user, session=session)
    user_unit_ids = [u.id for u in user_units]
    groups = session.exec(
        select(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(Unit.id.in_(user_unit_ids))
        .where(Term.start_at < date)
        .where(Term.end_at > date)
        .offset(offset).limit(limit)
    ).all()
    return groups

@router.get("/assignment_groups/{id}", response_model=AssignmentGroupPublicWithAssignments)
def get_assignment_group(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    group = session.get(AssignmentGroup, id)
    if not group: raise HTTPException(status_code=404, detail="Assignment group not found")
    return group

@router.get("/assignments", response_model=list[AssignmentPublicWithGroup])
def get_assignments(
    date : datetime = datetime.now(timezone.utc),
    exclude_complete : bool = True,
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):

    query = (
        select(UsersAssignments)
        .join(User)
        .join(Assignment)
        .join(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(User.id == user.id)
        .where(Term.start_at < date)
        .where(Term.end_at > date)
    )

    if exclude_complete:
        query = query.where(UsersAssignments.submitted == False)

    query = query.offset(offset).limit(limit)

    users_assignments = session.exec(query).all()

    assignments = [ua.assignment for ua in users_assignments]

    return assignments

@router.get("/assignments/{id}", response_model=AssignmentPublicWithGroup)
def get_assignment(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignment = session.get(Assignment, id)
    if not assignment: raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment 
