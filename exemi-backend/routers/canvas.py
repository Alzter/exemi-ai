from pydantic import TypeAdapter
from ..models import User, UserUpdate, UserPublic, UserPublicWithUnits, UsersUnits, UsersAssignments, UniversityAliasPublic, UsersUnitsPublic
from ..models import Term, TermCreate, TermPublic, TermUpdate
from ..models import Unit, UnitCreate, UnitPublicWithTerm, UnitUpdate
from ..models import Assignment, AssignmentCreate, AssignmentPublicWithGroup, AssignmentUpdate
from ..models import AssignmentGroup, AssignmentGroupCreate, AssignmentGroupPublicWithUnit, AssignmentGroupUpdate
from ..models_canvas import CanvasTerm, CanvasUnit, CanvasAssignment, CanvasSubmission, CanvasAssignmentWithSubmission, CanvasAssignmentGroup
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import get_session, get_current_user, get_current_magic, get_fallback_providers_from_user
from ..canvas_api import query_canvas
from pydantic import BaseModel
from typing import Literal
import asyncio
import json
import re

router = APIRouter()

canvas_terms_adapter = TypeAdapter(list[CanvasTerm])
canvas_units_adapter = TypeAdapter(list[CanvasUnit])
canvas_assignment_group_adapter = TypeAdapter(list[CanvasAssignmentGroup])
canvas_assignment_adapter = TypeAdapter(list[CanvasAssignmentWithSubmission])

class CanvasTermsResult(BaseModel):
    terms : list[CanvasTerm]
    university_name : str
class CanvasUnitsResult(BaseModel):
    units : list[CanvasUnit]
    university_name : str
class CanvasAssignmentGroupsResult(BaseModel):
    assignment_groups : list[CanvasAssignmentGroup] 
    university_name : str
class CanvasAssignmentsResult(BaseModel):
    assignments : list[CanvasAssignmentWithSubmission]
    university_name : str

@router.get("/canvas/terms", response_model=CanvasTermsResult)#tuple[list[CanvasTerm], str])
async def canvas_get_terms(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
) -> CanvasTermsResult:#tuple[list[CanvasTerm], str]:
    result : CanvasUnitsResult = await canvas_get_units(
        user=user,
        magic=magic,
        exclude_complete_units=exclude_complete_units,
        exclude_organisation_units=exclude_organisation_units
    )
    units : list[CanvasUnit] = result.units
    active_university_name : str = result.university_name
    
    # Obtain every term object from every unit the user is currently enrolled in.
    raw_terms = [unit.term for unit in units]
    
    # Remove all duplicates and sort by ID.
    terms = sorted(
        {term.id: term for term in raw_terms}.values(),
        key=lambda term: term.id
    )

    return CanvasTermsResult(terms=terms, university_name=active_university_name)

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
    #    return None
        from datetime import datetime
        data.start_at = datetime.now()
        data.end_at = datetime.now()

    return {
        "canvas_id" : data.id,
        "name" : data.name,
        "start_at" : data.start_at,
        "end_at" : data.end_at
    }

def update_user_active_university_name(
    active_university_name : str,
    user : User,
    session : Session
) -> User:
    """
    If a fallback university was used to
    retrieve the users' terms/units/assignments,
    update the user's "active_university_name"
    field to the name of the fallback university
    so we know which university is *really*
    being used to retrieve their Canvas
    information.
    """
    data = {"active_university_name" : active_university_name}
    user.sqlmodel_update(data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

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

    result : CanvasTermsResult = await canvas_get_terms(
        exclude_organisation_units=True,
        exclude_complete_units=True,
        user=user,
        magic=magic
    )

    canvas_terms : list[CanvasTerm] = result.terms
    active_university_name : str = result.university_name

    update_user_active_university_name(
        active_university_name=active_university_name,
        user=user,
        session=session
    )
    
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
    
@router.get("/canvas/units", response_model=CanvasUnitsResult)#tuple[list[CanvasUnit], str])
async def canvas_get_units(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
) -> CanvasUnitsResult:#tuple[list[CanvasUnit], str]:

    params = {"include":"term"}
    if exclude_complete_units: params["enrollment_state"] = "active"
    raw_units, active_university_name = await query_canvas(
        path="courses",
        magic=magic,
        provider=user.university_name,
        fallback_providers=get_fallback_providers_from_user(user),
        max_items=50,
        params=params
    )

    # return raw_units
    units = canvas_units_adapter.validate_json(raw_units)
    
    # Internally, Swinburne Organisation units have term ID 1
    # ("Default Term"), so we can exclude them with this check:
    if exclude_organisation_units:
        units = [unit for unit in units if unit.enrollment_term_id != 1]

    return CanvasUnitsResult(units=units, university_name=active_university_name)

@router.get("/canvas/units/colours", response_model=dict[int, str])
async def canvas_get_unit_colours(
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    """
    Obtain the hex codes of the colours
    for the user's Canvas units.

    Each colour is a 3 or 6 character long
    string representing a hex colour, e.g.:
    F00, AA00AA, 0B9BE3.

    Colours are NOT preceded with a hashtag
    and are ALWAYS in uppercase.
    """
    colours, _ = await query_canvas(path="users/self/colors", magic=magic, provider="swinburne")
    colours = json.loads(colours)["custom_colors"]
    
    colours_dict = {} 
    colour_extractor = re.compile(r"course_(\d+)")
    
    for course, colour in colours.items():
        match = colour_extractor.search(course)
        if match:
            course_id = int(match[1])
            colour = colour[1:].upper()
            colours_dict[course_id] = colour

    return colours_dict 

def parse_canvas_unit(data : CanvasUnit) -> dict | None:
    """
    Map CanvasUnit objects to dicts or None
    if they are not mappable.

    Args:
        data (CanvasTerm): The unit to parse.
    
    Returns:
        (dict | None): The data dictionary if the Term parsed correctly, else None if the term should be ignored.
    """

    name = data.name
    if data.original_name:
        name = data.original_name

    return {
        "name" : name,
        "canvas_id" : data.id,
        "apply_assignment_group_weights" : data.apply_assignment_group_weights
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

    result : CanvasUnitsResult = await canvas_get_units(
        exclude_organisation_units=True,
        exclude_complete_units=True,
        user=user,
        magic=magic
    )

    canvas_units : list[CanvasUnit] = result.units
    active_university_name : str = result.university_name

    canvas_unit_colours : dict[int,str] = await canvas_get_unit_colours(
        user=user,
        magic=magic
    )

    canvas_unit_nicknames : dict[int,str] = {}
    for unit in canvas_units:
        if unit.original_name is not None:
            canvas_unit_nicknames[unit.id] = unit.name
    
    update_user_active_university_name(
        active_university_name=active_university_name,
        user=user,
        session=session
    )

    if not canvas_units: return []

    canvas_ids = [t.id for t in canvas_units]
    
    # Obtain all units we want to update with new information
    existing_units = session.exec(
        select(Unit)
        .join(Term)
        .where(Unit.canvas_id.in_(canvas_ids))
        .where(Term.university_name == user.university_name)
    ).all()

    # Obtain a list of unique term Canvas IDs
    # for all of the Canvas unit objects.
    existing_term_ids = [u.term.id for u in canvas_units]
    existing_term_ids = list(set(existing_term_ids))

    # Obtain all unique existing terms from the units.
    existing_terms = session.exec(
        select(Term)
        .where(Term.canvas_id.in_(existing_term_ids))
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
            print("Term not found for unit {canvas_unit.name}")
            continue
            #raise HTTPException(status_code=404, detail=f"Term not found for unit {canvas_unit.name}")

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
        nickname_map=canvas_unit_nicknames,
        colour_map=canvas_unit_colours,
        session=session,
        user=user
    )

    return modified_units

def enrol_user_in_units(
    units : list[Unit],
    nickname_map : dict[int,str],
    colour_map : dict[int,str],
    session : Session,
    user : User
):
    session.refresh(user)

# ---- Track which assignments user SHOULD have ----
    valid_unit_ids = {u.id for u in units}

    # ---- Existing junction rows ----
    existing_rows = session.exec(
            select(UsersUnits).where(UsersUnits.user_id == user.id)
    ).all()

    existing_by_unit = {
        u.unit_id: u for u in existing_rows
    }

    # ---- Create / Update ----
    for unit in units:
        # canvas_assignment = canvas_by_id.get(assignment.canvas_id)
        # if not canvas_assignment:
        #     continue

        # update = parse_canvas_submission(
        #     canvas_assignment.submission
        # )
        
        if not unit.id: continue
        u = existing_by_unit.get(unit.id)
        
        unit_nickname = nickname_map.get(unit.canvas_id)
        unit_colour = colour_map.get(unit.canvas_id)
        
        update = {
            "nickname" : unit_nickname,
            "colour" : unit_colour
        }

        if not u:
            u = UsersUnits(
                user_id=user.id,
                unit_id=unit.id,
                **update
            )
            session.add(u)
        else:
            u.sqlmodel_update(update)

    # ---- Remove stale assignments ----
    for unit_id, u in existing_by_unit.items():
        if unit_id not in valid_unit_ids:
            session.delete(u)

    # for unit in units:
    #     if unit not in user.units:
    #         user.units.append(unit)
    # 
    # # Unenrol the user from any units
    # # they are no longer taking
    # for existing_unit in list(user.units):
    #     if existing_unit not in units:
    #         user.units.remove(existing_unit)
    
    # session.add(user)
    session.commit()
 
@router.get("/canvas/units/{unit_id}/assignment_groups", response_model = CanvasAssignmentGroupsResult)#tuple[list[CanvasAssignmentGroup], str])
async def canvas_get_assignment_groups(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
) -> CanvasAssignmentGroupsResult:#tuple[list[CanvasAssignmentGroup], str]:
    path = f"courses/{unit_id}/assignment_groups"
    params = {"include":["submission", "assignments"]}

    raw_assignment_groups, active_university_name = await query_canvas(
        path=path,
        magic=magic,
        provider=user.university_name,
        fallback_providers=get_fallback_providers_from_user(user),
        max_items=50,
        params=params
    )
    
    assignment_groups = canvas_assignment_group_adapter.validate_json(raw_assignment_groups)
    return CanvasAssignmentGroupsResult(assignment_groups=assignment_groups, university_name=active_university_name)


@router.get("/canvas/units/{unit_id}/assignments", response_model=CanvasAssignmentsResult)#tuple[list[CanvasAssignmentWithSubmission], str])
async def canvas_get_assignments(
    unit_id : int,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
) -> CanvasAssignmentsResult:#tuple[list[CanvasAssignmentWithSubmission], str]:
    path = f"courses/{unit_id}/assignments"
    params = {"include":"submission"}

    raw_assignments, active_university_name = await query_canvas(
        path=path,
        magic=magic,
        provider=user.university_name,
        fallback_providers=get_fallback_providers_from_user(user),
        max_items=50,
        params=params
    )

    assignments = canvas_assignment_adapter.validate_json(raw_assignments)

    return CanvasAssignmentsResult(assignments=assignments, university_name=active_university_name)

@router.get("/canvas/assignments", response_model = CanvasAssignmentsResult)#tuple[list[CanvasAssignmentWithSubmission], str])
async def canvas_get_all_assignments(
    exclude_complete_units : bool = True,
    exclude_organisation_units : bool = True,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
):
    units_result : CanvasUnitsResult = await canvas_get_units(
        exclude_organisation_units=exclude_complete_units,
        exclude_complete_units=exclude_organisation_units,
        user=user,
        magic=magic
    )

    units : list[CanvasUnit] = units_result.units
    active_university_name : str = units_result.university_name
    
    tasks = [
        canvas_get_assignments(
            unit_id=unit.id,
            user=user,
            magic=magic
        )
        for unit in units
    ]

    result : list[CanvasAssignmentsResult] = await asyncio.gather(*tasks)

    canvas_assignments = []
    for unit_assignments_result in result:
        canvas_assignments.extend(unit_assignments_result.assignments)
    
    return CanvasAssignmentsResult(assignments=canvas_assignments, university_name=active_university_name)

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
    
    user_units = session.exec(
        select(UsersUnits)
        .join(User)
        .where(User.id == user.id)
    ).all()

    unit_ids = [u.unit_id for u in user_units]

    units = session.exec(
        select(Unit)
        .where(Unit.id.in_(unit_ids))
    ).all()

    #user_with_units = UserPublicWithUnits.model_validate(user)
    #units = user_with_units.units

    # --------------------------------------------------
    # 1. Fetch Canvas groups WITH assignments
    # --------------------------------------------------
    all_canvas_groups: list[tuple[int, CanvasAssignmentGroup]] = []

    tasks = [
        canvas_get_assignment_groups(
            unit_id=unit.canvas_id,
            user=user,
            magic=magic,
        )
        for unit in units
    ]

    result : list[CanvasAssignmentGroupsResult] = await asyncio.gather(*tasks)

    for unit, groups in zip(units, [r.assignment_groups for r in result]):
        all_canvas_groups.extend((unit.id, g) for g in groups)
    
    if result:
        active_university_name = result[0].university_name
        update_user_active_university_name(
            active_university_name=active_university_name,
            user=user,
            session=session
        )

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
    session.refresh(user)
    
    canvas_assignments: list[CanvasAssignmentWithSubmission] = []

    unit_ids = list({
        assignment.group.unit.canvas_id
        for assignment in assignments
    })

    tasks = [
        canvas_get_assignments(
            unit_id=canvas_unit_id,
            user=user,
            magic=magic
        )
        for canvas_unit_id in unit_ids
    ]

    results : list[CanvasAssignmentsResult] = await asyncio.gather(*tasks)

    canvas_assignments = []
    for unit_assignments_result in results:
        canvas_assignments.extend(unit_assignments_result.assignments)

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
            ua.sqlmodel_update(update)

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
