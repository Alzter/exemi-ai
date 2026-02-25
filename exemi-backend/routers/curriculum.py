from ..models import User, UserPublicWithUnits, UsersAssignments, UsersUnits
from ..models import University
from ..models import Term, TermPublic, TermPublicWithUnits
from ..models import Unit,  UnitPublic, UnitPublicWithAssignmentGroups
from ..models import AssignmentGroup, AssignmentGroupPublicWithUnit, AssignmentGroupPublicWithAssignments
from ..models import Assignment, AssignmentPublic, AssignmentPublicWithGroup
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
    """
    Obtain every teaching period (term)
    stored in the system. Currently these
    are limited to biannual university
    semesters.

    Args:
        offset (int, optional):
            Pagination start index. Defaults to 0.
        limit (int, optional):
            Pagination length. Defaults to 100. Max of 100.
        user (User):
            The currently logged-in user.
        session (Session, optional):
            Active connection with the SQLModel database.

    Returns:
        list[TermPublic]: The teaching period.
    """
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
    """
    Obtain a term (teaching period) with all its units.

    Args:
        id (int): The term ID.
        user (User): The currently logged-in user.
        session (Session, optional): Active connection with the SQLModel database.

    Raises:
        HTTPException: If the term is not found, raises a 404.

    Returns:
        TermPublicWithUnits: The term with units included.
    """
    term = session.get(Term, id)
    if not term: raise HTTPException(status_code=404, detail="Term not found")
    return term

@router.get("/units", response_model=list[UnitPublic])
def get_units(
    date : datetime = datetime.now(timezone.utc),
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain the user's current units.

    Args:
        date (datetime, optional):
            Only obtain units which are active during this date. Defaults to datetime.now().
        offset (int, optional):
            Pagination start index. Defaults to 0.
        limit (int, optional):
            Pagination length. Defaults to 100. Max of 100.
        user (User):
            The currently logged-in user.
        session (Session, optional):
            Active connection with the SQLModel database.

    Returns:
        list[UnitPublic]: The user's units.
    """

    user_units = session.exec(
        select(UsersUnits)
        .join(Unit)
        .join(Term)
        .join(User)
        .where(User.id == user.id)
        .where(Term.start_at < date)
        .where(Term.end_at > date)
    ).all()

    unit_ids = [u.unit_id for u in user_units]

    units = session.exec(
        select(Unit)
        .where(Unit.id.in_(unit_ids))
    )

    return units
    # user_with_units = UserPublicWithUnits.model_validate(user)
    # return user_with_units.units

@router.get("/units/{id}", response_model=UnitPublicWithAssignmentGroups)
def get_unit(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a unit with all its assignment groups.

    Args:
        id (int): The unit ID.
        user (User): The currently logged-in user.
        session (Session, optional): Active connection with the SQLModel database.

    Raises:
        HTTPException: If the unit is not found, raises a 404.

    Returns:
        UnitPublicWithAssignmentGroups: The unit with assignment groups included.
    """
    unit = session.get(Unit, id)
    if not unit: raise HTTPException(status_code=404, detail="Unit not found")
    return unit

@router.get("/assignment_groups", response_model=list[AssignmentGroupPublicWithUnit])
def get_assignment_groups(
    date : datetime = datetime.now(timezone.utc),
    unit_id : int | None = None,
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain the user's current assignment groups
    along with their unit information.

    Args:
        date (datetime, optional):
            Only obtain assignment groups for units which are active during this date. Defaults to datetime.now().
        unit_id (int | None, optional):
            If given, only includes assignments from a given unit. Defaults to None.
        offset (int, optional):
            Pagination start index. Defaults to 0.
        limit (int, optional):
            Pagination length. Defaults to 100. Max of 100.
        user (User):
            The currently logged-in user.
        session (Session, optional):
            Active connection with the SQLModel database.

    Returns:
        list[AssignmentGroupPublicWithUnit]: The assignment groups with unit information included.
    """
    user_units = get_units(user=user, session=session)
    user_unit_ids = [u.id for u in user_units]

    query = (
        select(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(Unit.id.in_(user_unit_ids))
        .where(Term.start_at < date)
        .where(Term.end_at > date)
    )

    if unit_id is not None:
        query = query.where(Unit.id == unit_id)
    
    query = query.offset(offset).limit(limit)

    groups = session.exec(query).all()
    
    return groups

@router.get("/assignment_groups/{id}", response_model=AssignmentGroupPublicWithAssignments)
def get_assignment_group(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain an assignment group with all its assignments.

    Args:
        id (int): The assignment group ID.
        user (User): The currently logged-in user.
        session (Session, optional): Active connection with the SQLModel database.

    Raises:
        HTTPException: If the assignment group is not found, raises a 404.

    Returns:
        AssignmentGroupPublicWithAssignments: The assignment group with its assignments included.
    """
    group = session.get(AssignmentGroup, id)
    if not group: raise HTTPException(status_code=404, detail="Assignment group not found")
    return group

@router.get("/assignments", response_model=list[AssignmentPublic])
def get_assignments(
    date : datetime = datetime.now(timezone.utc),
    exclude_complete : bool = True,
    exclude_no_due_date : bool = True,
    exclude_ungraded : bool = False,
    unit_id : int | None = None,
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtains a list of assignments for the user.
    By default, this obtains only incomplete
    assignments for the user's current units
    which have a due date assigned.

    Args:
        date (datetime, optional):
            Only obtain assignments for units which are active during this date. Defaults to datetime.now().
        exclude_complete (bool, optional):
            Whether to exclude submitted assignments. Defaults to True.
        exclude_no_due_date (bool, optional):
            Exclude assignments which do not have a due date assigned. Defaults to True.
        exclude_ungraded (bool, optional):
            Exclude assignments which have zero points, and thus
            may not contribute to the final grade. Defaults to False.
        unit_id (int | None, optional):
            If given, only includes assignments from a given unit. Defaults to None.
        offset (int, optional):
            Pagination start index. Defaults to 0.
        limit (int, optional):
            Pagination length. Defaults to 100. Max of 100.
        user (User):
            The currently logged-in user.
        session (Session, optional):
            Active connection with the SQLModel database.

    Returns:
        list[AssignmentPublic]: The user's assignments.
    """

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

    if exclude_ungraded:
        query = query.where(Assignment.points > 0)
    
    if exclude_no_due_date:
        query = query.where(Assignment.due_at != None)

    if exclude_complete:
        query = query.where(UsersAssignments.submitted == False)

    if unit_id is not None:
        query = query.where(Unit.id == unit_id)

    query = query.offset(offset).limit(limit).order_by(Assignment.due_at)

    users_assignments = session.exec(query).all()

    assignments = [ua.assignment for ua in users_assignments]

    return assignments

@router.get("/assignments/{id}", response_model=AssignmentPublic)
def get_assignment(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignment = session.get(Assignment, id)
    if not assignment: raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment 
