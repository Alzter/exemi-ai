from pydantic import TypeAdapter
from ..models import User, UserCreate, UserUpdate, UserPublic
# from ..models import University, UniversityCreate, UniversityPublic
from ..models import Term, TermCreate, TermPublic
from ..models import Unit, UnitCreate, UnitPublic
from ..models import Assignment, AssignmentCreate, AssignmentPublic
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic

router = APIRouter()

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
async def get_terms(
    offset : int = 0,
    limit : int = Query(default=100, limit=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    terms = session.exec(
        select(Term).offset(offset).limit(limit)
    ).all()
    return terms 

@router.get("/term/{name}", response_model=TermPublic)
async def get_term(
    name : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    term = session.exec(
        select(Term).where(Term.name == name)
    ).first()
    if not term: raise HTTPException(status_code=404, detail="Term not found")
    return term

@router.post("/term", response_model=TermPublic)
async def create_term(
    data : TermCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    if not user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    term = Term.model_validate(data)
    session.add(term)
    session.commit()
    session.refresh(term)
    return term

@router.get("/units", response_model=list[UnitPublic])
async def get_units(
    offset : int = 0,
    limit : int = Query(default=100, limit=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    units = session.exec(
        select(Unit).offset(offset).limit(limit)
    ).all()
    return units

@router.get("/units/{name}", response_model=UnitPublic)
async def get_unit(
    name : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    unit = session.exec(
        select(Term).where(Unit.name == name)
    ).first()
    if not unit: raise HTTPException(status_code=404, detail="Unit not found")
    return unit 

@router.post("/unit", response_model=UnitPublic)
async def create_unit(
    data : UnitCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    if not user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    unit = Unit.model_validate(data)
    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit

@router.get("/assignments", response_model=list[AssignmentPublic])
async def get_assignments(
    offset : int = 0,
    limit : int = Query(default=100, limit=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignments = session.exec(
        select(Assignment).offset(offset).limit(limit)
    ).all()
    return assignments

@router.get("/units/{name}", response_model=UnitPublic)
async def get_assignment(
    name : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    assignment = session.exec(
        select(Assignment).where(Assignment.name == name)
    ).first()
    if not assignment: raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment 

@router.post("/assignment", response_model=AssignmentPublic)
async def create_assignment(
    data : AssignmentCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    if not user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    assignment = Assignment.model_validate(data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment

