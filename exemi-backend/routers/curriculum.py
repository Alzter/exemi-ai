from pydantic import BaseModel, TypeAdapter
from ..models import User, UsersAssignments, UsersUnits, UsersUnitsPublic
from ..models import University, UniversityPublic, UniversityPublicWithAliases, UniversityAlias, UniversityAliasPublic, UniversityAliasCreate, UniversityAliasUpdate
from ..models import Term, TermPublic, TermPublicWithUnits
from ..models import Unit,  UnitPublic, UnitPublicWithAssignmentGroups
from ..models import AssignmentGroup, AssignmentGroupPublicWithUnit, AssignmentGroupPublicWithAssignments
from ..models import Assignment, AssignmentPublic, AssignmentPublicWithGroup
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_current_user
from datetime import datetime, timezone
from ..date_utils import parse_timestamp, timestamp_to_string, get_days_remaining
from typing import Literal
import json

router = APIRouter()

@router.get("/university", response_model=list[UniversityPublic])
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

@router.get("/university/{name}", response_model=UniversityPublicWithAliases)
def get_university(
    name : str,
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user)
):
    """
    Obtain a given university and its alias list (ADMIN ONLY).
    
    Args:
        name (str): The name of the university to obtain.

    Returns:
        UniversityPublicWithAliases: The university and its aliases.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    existing_university = session.get(University, name)
    if not existing_university: raise HTTPException(status_code=404, detail="University not found")
    return existing_university

@router.post("/university_alias", response_model=UniversityPublicWithAliases)
def create_university_alias(
    data : UniversityAliasCreate,
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user)
):
    """
    Create an alias for a given university (ADMIN ONLY).

    Each university name correlates to a Canvas provider URL,
    (e.g., "swinburne" -> "swinburne.instructure.com")
    but certain universities may use multiple Canvas
    provider URLs depending on context.
    
    For example, Swinburne University use "swinburne" for
    on-campus students and "swinburneonline" for remote
    students. Using aliases allows users registered
    under the "swinburne" university to still be able
    to access their Canvas information if their Canvas URL
    is actually "swinburneonline".

    Args:
        data (UniversityAliasCreate): The university name and the alias name.

    Raises:
        HTTPException:
            Raises a 401 if the user is not an administrator.
            Raises a 404 if the original university does not exist.

    Returns:
        UniversityAliasPublic: The university alias.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")

    existing_university = session.get(University, data.university_name)
    if not existing_university: raise HTTPException(status_code=404, detail=f"University not found: {data.university_name}")

    alias = UniversityAlias.model_validate(data)
    
    session.add(alias)
    session.commit()
    session.refresh(existing_university)
    return existing_university

@router.delete("/university_alias/{id}", response_model=Literal[True])
def delete_university_alias(
    id : int,
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user)
):
    """
    Remove an alias for a given university (ADMIN ONLY).

    Args:
        id (int): The ID for the existing university alias.

    Raises:
        HTTPException:
            Raises a 401 if the user is not an administrator.
            Raises a 404 if the alias does not exist.

    Returns:
        Literal[True]: Returns True if the deletion was successful.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")

    existing_alias = session.get(UniversityAlias, id)
    if not existing_alias: raise HTTPException(status_code=404, detail="University alias not found")
    session.delete(existing_alias)
    session.commit()
    return True

@router.patch("/university_alias/{id}", response_model=UniversityAliasPublic)
def update_university_alias(
    id : int,
    data : UniversityAliasUpdate,
    session : Session = Depends(get_session),
    current_user : User = Depends(get_current_user)
):
    """
    For a given university, replace an alias
    name with another alias name (ADMIN ONLY).

    Args:
        id (int): The ID for the existing university alias.
        data (UniversityAliasUpdate): The new name to use.

    Raises:
        HTTPException:
            Raises a 401 if the user is not an administrator.
            Raises a 404 if the alias does not exist.

    Returns:
        UniversityAliasPublic: The updated university alias.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    
    existing_alias = session.get(UniversityAlias, id)
    if not existing_alias: raise HTTPException(status_code=404, detail="University alias not found")
    
    update = data.model_dump(exclude_unset=True)

    existing_alias.sqlmodel_update(update) 
    
    session.add(existing_alias)
    session.commit()
    session.refresh(existing_alias)
    return existing_alias

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

@router.get("/user_units", response_model=list[UsersUnitsPublic])
def get_user_units(
    date : datetime = datetime.now(timezone.utc),
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain the user's current units, including
    the user-assigned unit colour and nickname
    for each unit.

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
        list[UsersUnitsPublic]: The user's units.
    """

    user_units = session.exec(
        select(UsersUnits)
        .join(Unit)
        .join(Term)
        .join(User)
        .where(User.id == user.id)
        .where(Term.start_at < date)
        .where(Term.end_at > date)
        .offset(offset)
        .limit(limit)
    ).all()
    
    return user_units

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

    user_units = get_user_units(
        date=date,
        offset=offset,
        limit=limit,
        user=user,
        session=session
    ) 

    unit_ids = [u.unit_id for u in user_units]
    
    units = session.exec(
        select(Unit)
        .where(Unit.id.in_(unit_ids))
    )

    return units

class UnitJSON(BaseModel):
    id : int
    name: str
    nickname : str | None
    url: str

units_list_adapter = TypeAdapter(list[UnitJSON])

@router.get("/tool/units_json", response_model=str)
def get_units_list_json(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> str:
    """
    Returns the student's units in JSON format.
    """
    university_name = user.active_university_name or user.university_name

    user_units = get_user_units(offset=0, limit=100, user=user, session=session)
    user_units = [UsersUnitsPublic.model_validate(u) for u in user_units]

    unit_list : list[UnitJSON] = []

    for user_unit in user_units:
        url = f"https://www.{university_name}.instructure.com/"
        url += f"courses/{user_unit.unit.canvas_id}/"

        unit_list.append(
            UnitJSON(
                id = user_unit.unit.id,
                name = user_unit.unit.readable_name,
                nickname = user_unit.nickname,
                url = url
            )
        )

    # units_list = [unit.readable_name for unit in units]

    return units_list_adapter.dump_json(unit_list).decode("utf-8")

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

# @router.get("/tool/assignments")
# def get_assignments_list(
#     user : User = Depends(get_current_user),
#     session : Session = Depends(get_session)
# ) -> str:
#     """
#     Create a markdown-formatted list of
#     the student's incomplete assignments
#     organised by unit, sorted by due date.

#     Returns:
#         str: List of the student's incomplete assignments.
#     """

#     message : list[str] = ["# Assignments:\n"]

#     units = get_units(user=user, session=session, offset=0, limit=100)
#     units = [UnitPublic.model_validate(u) for u in units]

#     units_by_id : dict[int, Unit] = {u.id : u for u in units}
#     units_assignments : dict[int, list[AssignmentPublic]] = {}

#     university_name = user.active_university_name or user.university_name

#     for unit in units:

#         assignments = get_assignments(user=user, session=session, unit_id=unit.id, offset=0, limit=100)
#         assignments = [AssignmentPublic.model_validate(a) for a in assignments]

#         units_assignments[unit.id] = assignments

#     for unit_id, assignments in units_assignments.items():
#         if not assignments: continue

#         unit = units_by_id.get(unit_id)
#         if not unit: raise HTTPException(status_code=404, detail=f"Unit not found: {unit_id}")
        
#         message.append(f"## Unit: {unit.readable_name}\n")

#         for assignment in assignments:
#             url = f"https://www.{university_name}.instructure.com/"
#             url += f"courses/{unit.canvas_id}/"
#             url += f"assignments/{assignment.canvas_id}"

#             due_date_string = timestamp_to_string(parse_timestamp(assignment.due_at))

#             message.append(f"### {assignment.name}")
#             if assignment.description:
#                 message.append(f"Description:\n```html\n{assignment.description}\n```")
#             message.append(f"- **Due date:** {due_date_string}")
#             message.append(f"- **Grade contribution:** {int(assignment.grade_contribution * 100)}%")
#             message.append(f"- **Requires group work:** {"YES" if assignment.is_group else "NO"}")
#             message.append(f"- **URL**: {url}")
#             message.append("\n")

#     return "\n".join(message).strip()

class AssignmentJSON(BaseModel):
    name: str
    description: str | None
    due_date: datetime | None
    days_remaining : int | None
    grade_contribution: int
    is_group: bool
    url: str

class UnitAssignmentsJSON(BaseModel):
    unit_id : int
    unit_name: str
    assignments: list[AssignmentJSON]

assignments_list_adapter = TypeAdapter(list[UnitAssignmentsJSON])

@router.get("/tool/assignments_json", response_model=str)#list[UnitAssignmentsJSON])
def get_assignments_list_json(
    unit_id : int | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Return the student's incomplete assignments in JSON format,
    organized by unit and sorted by due date.

    Args:
        unit_id (int | None, optional): Which unit to obtain assignment information for. If not given, returns assignments for all units. Defaults to None.
    """

    # Fetch units
    units = get_units(user=user, session=session, offset=0, limit=100)
    units = [UnitPublic.model_validate(u) for u in units]

    #units_by_id: dict[int, Unit] = {u.id: u for u in units}
    units_assignments_json: list[UnitAssignmentsJSON] = []

    university_name = user.active_university_name or user.university_name

    for unit in units:
        if unit_id is not None and unit.id != unit_id:
            continue
        
        assignments = get_assignments(user=user, session=session, unit_id=unit.id, offset=0, limit=100)
        assignments = [AssignmentPublic.model_validate(a) for a in assignments]

        assignment_list: list[AssignmentJSON] = []
        for assignment in assignments:
            url = f"https://www.{university_name}.instructure.com/"
            url += f"courses/{unit.canvas_id}/assignments/{assignment.canvas_id}"

            # due_date_string = timestamp_to_string(parse_timestamp(assignment.due_at))
            days_remaining = get_days_remaining(assignment.due_at)

            assignment_list.append(
                AssignmentJSON(
                    name=assignment.name or "",
                    description=assignment.readable_description,
                    due_date=parse_timestamp(assignment.due_at),
                    days_remaining=days_remaining,
                    #due_date=due_date_string,
                    grade_contribution=int(assignment.grade_contribution * 100),
                    is_group=assignment.is_group,
                    url=url
                )
            )

        if assignment_list:
            units_assignments_json.append(
                UnitAssignmentsJSON(
                    unit_id=unit.id,
                    unit_name=unit.readable_name,
                    assignments=assignment_list
                )
            )

    return assignments_list_adapter.dump_json(units_assignments_json).decode("utf-8")
