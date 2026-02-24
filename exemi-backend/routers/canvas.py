from pydantic import TypeAdapter
from ..models import University, User, UserCreate, UserUpdate, UserPublic
# from ..models import University, UniversityCreate, UniversityPublic
from ..models import Term, TermCreate, TermPublic, TermUpdate
from ..models import Unit, UnitCreate, UnitPublic, UnitUpdate
from ..models import Assignment, AssignmentCreate, AssignmentPublic, AssignmentPublicWithGroup, AssignmentUpdate
from ..models import AssignmentGroup, AssignmentGroupCreate, AssignmentGroupPublicWithUnit, AssignmentGroupUpdate
from ..models_canvas import CanvasTerm, CanvasUnit, CanvasAssignment, CanvasAssignmentGroup, CanvasAssignmentGroupWithAssignments
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas

router = APIRouter()

canvas_terms_adapter = TypeAdapter(list[CanvasTerm])
canvas_units_adapter = TypeAdapter(list[CanvasUnit])
canvas_assignment_group_adapter = TypeAdapter(list[CanvasAssignmentGroup])
canvas_assignment_group_with_assignments_adapter = TypeAdapter(list[CanvasAssignmentGroupWithAssignments])
canvas_assignment_group_individual_adapter = TypeAdapter(CanvasAssignmentGroupWithAssignments)

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

def parse_canvas_term(data : CanvasTerm) -> dict | None:
    """
    Map CanvasTerm objects to dicts
    which can be used to create
    TermCreate or TermUpdate models.
    If a term is NOT suitable to be
    created (lacks a start or end date),
    return None, meaning IGNORE the
    current term.

    Args:
        data (CanvasTerm): The term to parse.
    
    Returns:
        (dict | None): The data dictionary if the Term parsed correctly, else None if the term should be ignored.
    """

    if (not data.start_at or not data.end_at):
        return None
    return {
        "canvas_id" : data.id,
        "name" : data.name,
        "start_at" : data.start_at,
        "end_at" : data.end_at
    }

@router.post("/canvas/terms", response_model=list[TermPublic])
async def commit_canvas_terms(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    magic: str = Depends(get_current_magic)
):
    """
    Sync Canvas terms into DB:
    - Create if missing
    - Update if existing
    """

    canvas_terms: list[CanvasTerm] = await canvas_get_terms(user=user, magic=magic)
    if not canvas_terms: return []
    
    canvas_ids = [t.id for t in canvas_terms]
    
    # Obtain all terms we want to update with new information
    existing_terms = session.exec(
        select(Term)
        .where(Term.canvas_id.in_(canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()
    
    # Map all existing terms by their Canvas ID
    existing_terms_by_canvas_id : dict[int, Term] = {t.canvas_id: t for t in existing_terms}
    
    # Create a list of the new terms
    modified_terms: list[Term] = []

    for canvas_term in canvas_terms:
        data = parse_canvas_term(canvas_term)
        if not data: continue

        data["university_name"] = user.university_name

        existing_term = existing_terms_by_canvas_id.get(
            canvas_term.id
        )

        if existing_term:
            update_data = TermUpdate.model_validate(data).model_dump(exclude_unset=True)
            
            # Only modify fields which were changed
            changed = False
            for k, v in update_data.items():
                if getattr(existing_term, k) != v:
                    setattr(existing_term, k, v)
                    changed = True

            if changed:
                session.add(existing_term)

            modified_terms.append(existing_term)
        else:
            new_term = Term.model_validate(
                TermCreate.model_validate(data)
            )
            session.add(new_term)
            modified_terms.append(new_term)

    session.commit()

    for term in modified_terms:
        session.refresh(term)

    return modified_terms
    
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

def parse_canvas_unit(data : CanvasUnit) -> dict | None:
    """
    Map CanvasTerm objects to dicts or None
    if they are not mappable.

    Args:
        data (CanvasTerm): The term to parse.
    
    Returns:
        (dict | None): The data dictionary if the Term parsed correctly, else None if the term should be ignored.
    """

    name = data.name
    if data.original_name:
        name = data.original_name

    return {
        "name" : name,
        "canvas_id" : data.id
    }

@router.post("/canvas/units", response_model=list[UnitPublic])
async def commit_canvas_units(
    session : Session = Depends(get_session),
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    """
    Sync Canvas units into DB:
    - Create if missing
    - Update if existing

    Preconditions:
    - POST /canvas/terms
    """

    existing_terms : list[Term] = await commit_canvas_terms(session=session,user=user,magic=magic)

    canvas_units: list[CanvasUnit] = await canvas_get_units(exclude_complete_units=False, user=user, magic=magic)
    if not canvas_units: return []

    canvas_ids = [t.id for t in canvas_units]
    
    # Obtain all units we want to update with new information
    existing_units = session.exec(
        select(Unit)
        .join(Term)
        .where(Unit.canvas_id.in_(canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    # Map all existing units by their Canvas ID
    existing_units_by_canvas_id : dict[int, Unit] = {t.canvas_id: t for t in existing_units}
    existing_terms_by_canvas_id : dict[int, Term] = {t.canvas_id: t for t in existing_terms}
    
    # Create a list of the new units
    modified_units: list[Unit] = []
    
    for canvas_unit in canvas_units:
        data = parse_canvas_unit(canvas_unit)
        if not data: continue

        existing_term = existing_terms_by_canvas_id.get(
            canvas_unit.term.id
        )

        data["term_id"] = existing_term.id

        existing_unit = existing_units_by_canvas_id.get(
            canvas_unit.id
        )

        if existing_unit:
            update_data = UnitUpdate.model_validate(data).model_dump(exclude_unset=True)
            
            # Only modify fields which were changed
            changed = False
            for k, v in update_data.items():
                if getattr(existing_unit, k) != v:
                    setattr(existing_unit, k, v)
                    changed = True

            if changed:
                session.add(existing_unit)

            modified_units.append(existing_unit)

        else:

            new_unit = Unit.model_validate(
                UnitCreate.model_validate(data)
            )
            session.add(new_unit)
            modified_units.append(new_unit)

    session.commit()

    for unit in modified_units:
        session.refresh(unit)

    enrol_user_in_units(
        units=modified_units,
        session=session,
        user=user
    )

    return modified_units

def enrol_user_in_units(
    units : list[Unit],
    session : Session,
    user : User
):
    for unit in units:
        if unit not in user.units:
            user.units.append(unit)
    
    session.add(user)
    session.commit()
 
@router.get("/canvas/units/{unit_id}/assignment_groups", response_model = list[CanvasAssignmentGroup])
async def canvas_get_assignment_groups(
    unit_id : int,
    include_assignments : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":"assignments"} if include_assignments else {}
    adapter = canvas_assignment_group_with_assignments_adapter if include_assignments else canvas_assignment_group_adapter

    raw_assignment_groups = await query_canvas(path=path, magic=magic, provider=user.university_name, max_items=50, params=params)
    
    assignment_groups = adapter.validate_json(raw_assignment_groups)
    return assignment_groups

@router.get("/canvas/units/{unit_id}/assignment_group/{group_id}", response_model=CanvasAssignmentGroupWithAssignments)
async def canvas_get_assignment_group(
    unit_id : int,
    group_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    path = f"courses/{unit_id}/assignment_groups/{group_id}"
    params = {"include":"assignments"}
    raw_assignment_group = await query_canvas(path=path, magic=magic, provider=user.university_name, max_items=50, params=params)
    assignment_group = canvas_assignment_group_individual_adapter.validate_json(raw_assignment_group)
    return assignment_group

def parse_canvas_assignment_group(data : AssignmentGroup) -> dict | None:
    return {
        "name" : data.name,
        "canvas_id" : data.id,
        "group_weight" : data.group_weight
    }

@router.post("/canvas/assignment_groups", response_model=list[AssignmentGroupPublicWithUnit])
async def commit_canvas_assignment_groups(
    session : Session = Depends(get_session),
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    """
    Sync Canvas assignment groups into DB:
    - Create if missing
    - Update if existing

    Preconditions:
    - POST /canvas/units
    - POST /canvas/terms
    """

    existing_units: list[Unit] = await commit_canvas_units(session=session, user=user, magic=magic)
    
    all_canvas_groups: list[tuple[int, CanvasAssignmentGroup]] = []

    # 1. Fetch Canvas assignment groups for all units concurrently
    for unit in existing_units:
        groups: list[CanvasAssignmentGroup] = await canvas_get_assignment_groups(
            unit_id=unit.canvas_id,
            include_assignments=False,
            user=user,
            magic=magic
        )
        all_canvas_groups.extend((unit.id, g) for g in groups)

    if not all_canvas_groups:
        return []

    # 2. Gather all canvas_ids and unit_ids
    canvas_ids = [g.id for _, g in all_canvas_groups]
    unit_ids = [unit.id for unit in existing_units]

    # 3. Batch query existing groups for this university
    existing_groups = session.exec(
        select(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(AssignmentGroup.canvas_id.in_(canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    existing_groups_by_canvas_unit: dict[tuple[int, int], AssignmentGroup] = {
        (g.unit_id, g.canvas_id): g for g in existing_groups
    }

    modified_groups: list[AssignmentGroup] = []

    # 4. Insert/update in bulk
    for unit_id, canvas_group in all_canvas_groups:
        data = parse_canvas_assignment_group(canvas_group)
        if not data:
            continue
        data["unit_id"] = unit_id

        key = (unit_id, canvas_group.id)
        existing_group = existing_groups_by_canvas_unit.get(key)

        if existing_group:
            update_data = AssignmentGroupUpdate.model_validate(data).model_dump(exclude_unset=True)
            changed = False
            for k, v in update_data.items():
                if getattr(existing_group, k) != v:
                    setattr(existing_group, k, v)
                    changed = True
            if changed:
                session.add(existing_group)
            modified_groups.append(existing_group)
        else:
            new_group = AssignmentGroup.model_validate(
                AssignmentGroupCreate.model_validate(data)
            )
            session.add(new_group)
            modified_groups.append(new_group)

    # 5. Commit once
    session.commit()
    for g in modified_groups:
        session.refresh(g)

    return modified_groups

def parse_canvas_assignment(data : CanvasAssignment) -> dict | None:

    is_group : bool = data.group_category_id is not None
    points : int = data.points_possible or 0
    description : str = data.description or ""

    if data.omit_from_final_grade:
        points = 0

    return {
        "canvas_id" : data.id,
        "name" : data.name,
        "points" : points,
        "description" : description,
        "due_at" : data.due_at,
        "is_group" : is_group
    }

@router.post("/canvas/assignments", response_model=list[AssignmentPublicWithGroup])
async def commit_canvas_assignments(
    session : Session = Depends(get_session),
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    existing_groups : list[AssignmentGroup] = await commit_canvas_assignment_groups(
        session = session,
        user = user,
        magic = magic
    )

    existing_groups : list[AssignmentGroupPublicWithUnit] = [AssignmentGroupPublicWithUnit.model_validate(g) for g in existing_groups]

    all_canvas_assignments : list[tuple[int, CanvasAssignment]] = []

    for group in existing_groups:
        group_data : list[CanvasAssignment] = await canvas_get_assignment_group(
            unit_id = group.unit.canvas_id,
            group_id = group.canvas_id,
            user=user,
            magic=magic
        )

        assignments = group_data.assignments

        all_canvas_assignments.extend((group.id, a) for a in assignments)
    
    if not all_canvas_assignments:
        return []
    
    canvas_ids = [a.id for _, a in all_canvas_assignments]
    group_ids = [group.id for group in existing_groups]

    existing_assignments = session.exec(
        select(Assignment)
        .join(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(Assignment.canvas_id.in_(canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    existing_assignments_by_group : dict[tuple[int,int], Assignment] = {
        (a.group_id, a.canvas_id): a for a in existing_assignments
    }

    modified_assignments : list[Assignment] = []

    for group_id, canvas_assignment in all_canvas_assignments:
        data = parse_canvas_assignment(canvas_assignment)
        if not data:
            continue
        data["group_id"] = group_id

        key = (group_id, canvas_assignment.id)
        existing_assignment = existing_assignments_by_group.get(key)

        if existing_assignment:
            update_data = AssignmentUpdate.model_validate(data).model_dump(exclude_unset=True)
            changed = False
            for k, v in update_data.items():
                if getattr(existing_assignment, k) != v:
                    setattr(existing_assignment, k, v)
                    changed = True
            if changed:
                session.add(existing_assignment)
            modified_assignments.append(existing_assignment)
        else:
            new_assignment = Assignment.model_validate(
                AssignmentCreate.model_validate(data)
            )
            session.add(new_assignment)
            modified_assignments.append(new_assignment)
    
    session.commit()
    for a in modified_assignments:
        session.refresh(a)

    return modified_assignments

@router.get("/canvas/units/{unit_id}/assignments", response_model=list[CanvasAssignment])
async def canvas_get_assignments(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    assignment_groups = await canvas_get_assignment_groups(unit_id=unit_id, user=user, magic=magic)
    
    assignments = []
    for group in assignment_groups:
        assignments.extend(group.assignments)

    return assignments

# @router.get("/canvas/assignment_groups", response_model = list[CanvasAssignmentGroupWithAssignments])
# async def canvas_get_all_assignment_groups(
#     exclude_complete_units : bool = True,
#     exclude_organisation_units : bool = True,
#     user : User = Depends(get_current_user),
#     magic : str = Depends(get_current_magic)
# ):
#     units : list[CanvasUnit] = await canvas_get_units(
#         exclude_complete_units=exclude_complete_units,
#         exclude_organisation_units=exclude_organisation_units,
#         user=user, magic=magic)
    
#     groups = []
#     for unit in units:
#         unit_assignment_groups = await canvas_get_assignment_groups(unit_id=unit.id, user=user, magic=magic)
#         groups.extend(unit_assignment_groups)
    
#     return groups

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

