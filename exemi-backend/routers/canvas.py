from pydantic import TypeAdapter
from ..models import University, User, UserCreate, UserUpdate, UserPublic, UserPublicWithUnits, UsersAssignments
# from ..models import University, UniversityCreate, UniversityPublic
from ..models import Term, TermCreate, TermPublic, TermUpdate
from ..models import Unit, UnitCreate, UnitPublic, UnitPublicWithTerm, UnitUpdate
from ..models import Assignment, AssignmentCreate, AssignmentPublic, AssignmentPublicWithGroup, AssignmentUpdate
from ..models import AssignmentGroup, AssignmentGroupCreate, AssignmentGroupPublicWithUnit, AssignmentGroupUpdate
from ..models_canvas import CanvasTerm, CanvasUnit, CanvasAssignment, CanvasSubmission, CanvasAssignmentWithSubmission, CanvasAssignmentGroup
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic
from ..canvas_api import query_canvas
from typing import Literal

router = APIRouter()

canvas_terms_adapter = TypeAdapter(list[CanvasTerm])
canvas_units_adapter = TypeAdapter(list[CanvasUnit])
canvas_assignment_group_adapter = TypeAdapter(list[CanvasAssignmentGroup])
canvas_assignment_adapter = TypeAdapter(list[CanvasAssignmentWithSubmission])

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
            
            existing_term.sqlmodel_update(update_data)

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

@router.post("/canvas/units", response_model=list[UnitPublicWithTerm])
async def commit_canvas_units(
    session : Session = Depends(get_session),
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    """
    Sync Canvas units into DB:
    - Create if missing
    - Update if existing

    Preconditions (call these functions first):
    - POST /canvas/terms
    """

    existing_terms = session.exec(
        select(Term)
    ).all()

    # existing_terms : list[Term] = await commit_canvas_terms(session=session,user=user,magic=magic)

    canvas_units: list[CanvasUnit] = await canvas_get_units(user=user, magic=magic)
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

        if not existing_term:
            raise HTTPException(status_code=404, detail=f"Term not found for unit {canvas_unit.name}")

        data["term_id"] = existing_term.id

        existing_unit = existing_units_by_canvas_id.get(
            canvas_unit.id
        )

        if existing_unit:
            update_data = UnitUpdate.model_validate(data).model_dump(exclude_unset=True)
            
            existing_unit.sqlmodel_update(update_data)

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
    
    # Unenrol the user from any units
    # they are no longer taking
    for existing_unit in user.units:
        if existing_unit not in units:
            user.units.remove(existing_unit)
    
    session.add(user)
    session.commit()
 
@router.get("/canvas/units/{unit_id}/assignment_groups")#, response_model = list[CanvasAssignmentGroup])
async def canvas_get_assignment_groups(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
):
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":["submission", "assignments"]}

    raw_assignment_groups = await query_canvas(path=path, magic=magic, provider=user.university_name, max_items=50, params=params)
    
    assignment_groups = canvas_assignment_group_adapter.validate_json(raw_assignment_groups)
    return assignment_groups


@router.get("/canvas/units/{unit_id}/assignments", response_model=list[CanvasAssignmentWithSubmission])
async def canvas_get_assignments(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    path = f"courses/{unit_id}/assignments"
    params = {"include":["submission", "submission"]}

    raw_assignments = await query_canvas(path=path, magic=magic, provider=user.university_name, max_items=50, params=params)
    # assignment_groups = await canvas_get_assignment_groups(unit_id=unit_id, user=user, magic=magic)
    
    # assignments = []
    # for group in assignment_groups:
    #     assignments.extend(group.assignments)
    assignments = canvas_assignment_adapter.validate_json(raw_assignments)

    return assignments

@router.get("/canvas/assignments", response_model = list[CanvasAssignmentWithSubmission])
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

def parse_canvas_assignment_group(data : CanvasAssignmentGroup) -> dict | None:
    return {
        "name" : data.name,
        "canvas_id" : data.id,
        "group_weight" : data.group_weight
    }

def parse_canvas_assignment(data : CanvasAssignment) -> dict | None:
    is_group : bool = data.group_category_id is not None
    points : float = data.points_possible or 0
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
async def commit_canvas_groups_and_assignments(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    magic: str = Depends(get_current_magic),
):
    """
    Sync Canvas assignments and assignment groups into DB:
    - Create if missing
    - Update if existing

    Preconditions (call these functions first):
    - POST /canvas/units
    - POST /canvas/terms
    """

    units = session.exec(
        select(Unit)
    ).all()

    # units = await commit_canvas_units(session=session, user=user, magic=magic)

    # --------------------------------------------------
    # 1. Fetch Canvas groups WITH assignments
    # --------------------------------------------------
    all_canvas_groups: list[tuple[int, CanvasAssignmentGroup]] = []

    for unit in units:
        groups = await canvas_get_assignment_groups(
            unit_id=unit.canvas_id,
            user=user,
            magic=magic,
        )
        all_canvas_groups.extend((unit.id, g) for g in groups)

    if not all_canvas_groups:
        return []

    # --------------------------------------------------
    # 2. Bulk fetch existing AssignmentGroups
    # --------------------------------------------------
    group_canvas_ids = [g.id for _, g in all_canvas_groups]

    existing_groups = session.exec(
        select(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(AssignmentGroup.canvas_id.in_(group_canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    existing_groups_by_key = {
        (g.unit_id, g.canvas_id): g for g in existing_groups
    }

    modified_groups: list[AssignmentGroup] = []

    # --------------------------------------------------
    # 3. Upsert AssignmentGroups
    # --------------------------------------------------
    for unit_id, cg in all_canvas_groups:
        data = parse_canvas_assignment_group(cg)
        if not data:
            continue
        data["unit_id"] = unit_id

        key = (unit_id, cg.id)
        existing = existing_groups_by_key.get(key)

        if existing:
            update = AssignmentGroupUpdate.model_validate(data).model_dump(exclude_unset=True)
            existing.sqlmodel_update(update)
            modified_groups.append(existing)
        else:
            new = AssignmentGroup.model_validate(AssignmentGroupCreate.model_validate(data))
            session.add(new)
            modified_groups.append(new)

    session.flush()  # Needed so new groups get IDs

    # Map canvas group → DB group_id
    group_id_lookup = {
        (g.unit_id, g.canvas_id): g.id for g in modified_groups
    }

    # --------------------------------------------------
    # 4. Collect all assignments
    # --------------------------------------------------
    all_canvas_assignments: list[tuple[int, CanvasAssignment]] = []

    for unit_id, cg in all_canvas_groups:
        group_id = group_id_lookup.get((unit_id, cg.id))
        if not group_id:
            continue
        for a in cg.assignments:
            all_canvas_assignments.append((group_id, a))

    if not all_canvas_assignments:
        session.commit()
        return []
    
    # --------------------------------------------------
    # 5. Bulk fetch existing Assignments
    # --------------------------------------------------
    assignment_canvas_ids = [a.id for _, a in all_canvas_assignments]

    existing_assignments = session.exec(
        select(Assignment)
        .join(AssignmentGroup)
        .join(Unit)
        .join(Term)
        .where(Assignment.canvas_id.in_(assignment_canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    existing_assignments_by_key = {
        (a.group_id, a.canvas_id): a for a in existing_assignments
    }

    modified_assignments: list[Assignment] = []

    # --------------------------------------------------
    # 6. Upsert Assignments
    # --------------------------------------------------
    for group_id, ca in all_canvas_assignments:
        data = parse_canvas_assignment(ca)
        if not data:
            continue
        data["group_id"] = group_id

        key = (group_id, ca.id)
        existing = existing_assignments_by_key.get(key)

        if existing:
            update = AssignmentUpdate.model_validate(data).model_dump(exclude_unset=True)
            existing.sqlmodel_update(update)
            modified_assignments.append(existing)
        else:
            new = Assignment.model_validate(AssignmentCreate.model_validate(data))
            session.add(new)
            modified_assignments.append(new)

    # --------------------------------------------------
    # 7. Commit once
    # --------------------------------------------------
    session.commit()

    for assignment in modified_assignments:
        session.refresh(assignment)

    canvas_assignments = [a[1] for a in all_canvas_assignments]

    await enrol_user_in_assignments(
        assignments=modified_assignments,
        session=session,
        magic=magic,
        user=user
    )

    return modified_assignments

def parse_canvas_submission(
    data : CanvasSubmission
) -> dict:
    
    is_submitted = False
    if data.workflow_state != "unsubmitted":
        is_submitted = True
    if data.excused:
        is_submitted = True
    
    return {
        "submitted" : is_submitted,
        "submitted_at" : data.submitted_at
    }

async def enrol_user_in_assignments(
    assignments: list[Assignment],
    session: Session,
    magic: str,
    user: User
):
    canvas_assignments: list[CanvasAssignmentWithSubmission] = []

    unit_ids = list({
        assignment.group.unit.canvas_id
        for assignment in assignments
    })

    for canvas_unit_id in unit_ids:
        unit_assignments = await canvas_get_assignments(
            unit_id=canvas_unit_id,
            user=user,
            magic=magic
        )
        canvas_assignments.extend(unit_assignments)

    canvas_by_id = {a.id: a for a in canvas_assignments}

    # ---- Track which assignments user SHOULD have ----
    valid_assignment_ids = {a.id for a in assignments}

    # ---- Existing junction rows ----
    stmt = select(UsersAssignments).where(
        UsersAssignments.user_id == user.id
    )
    existing_rows = session.exec(stmt).all()
    existing_by_assignment = {
        ua.assignment_id: ua for ua in existing_rows
    }

    # ---- Create / Update ----
    for assignment in assignments:
        canvas_assignment = canvas_by_id.get(assignment.canvas_id)
        if not canvas_assignment:
            continue

        update = parse_canvas_submission(
            canvas_assignment.submission
        )

        ua = existing_by_assignment.get(assignment.id)

        if not ua:
            ua = UsersAssignments(
                user_id=user.id,
                assignment_id=assignment.id,
                **update
            )
            session.add(ua)
        else:
            ua.sqlmodel_update(update, exclude_unset=True)

    # ---- Remove stale assignments ----
    for assignment_id, ua in existing_by_assignment.items():
        if assignment_id not in valid_assignment_ids:
            session.delete(ua)

    session.commit()

@router.post("/canvas/all", response_model = Literal[True])
async def sync_canvas_to_db(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session),
    magic : str = Depends(get_current_magic)
):
    """
    Synchronises the current user's terms, units,
    assignment groups, and assignments from Canvas
    into the database.

    For each term/unit/assignment group/assignment:
    - Creates if missing
    - Updates if existing

    Args:
        user (User): The currently logged-in user.
        session (Session): SQLModel connection with the database.
        magic (str): The user's magic..

    Raises:
        HTTPException: Raises a 500 if any stage of the process fails.

    Returns:
        Literal[True]: Returns True if the process succeeded.
    """
    try:
        await commit_canvas_terms(user=user, session=session, magic=magic)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error downloading semester information from Canvas! Error message: {str(e)}")
    
    try:
        await commit_canvas_units(user=user, session=session, magic=magic)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error downloading units from Canvas! Error message: {str(e)}")
    
    try:
        await commit_canvas_groups_and_assignments(user=user, session=session, magic=magic)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error downloading assignments from Canvas! Error message: {str(e)}")
    
    return True
