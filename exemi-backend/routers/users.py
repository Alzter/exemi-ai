from ..models import User, UserCreate, UserUpdate, UserPublic
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from ..dependencies import get_session, get_secret_key, encrypt_magic
from ..dependencies import get_current_user as root_get_current_user
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
PasswordHasher = PasswordHash.recommended()
LOGIN_SESSION_EXPIRY = timedelta(minutes=30)
router = APIRouter()

# @router.get("/users/", response_model = list[UserPublic])
def get_users(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    users = session.exec(
        select(User).offset(offset).limit(limit)
    ).all()
    return users

# @router.get("/users/{user_id}", response_model = UserPublic)
# def get_user(user_id : int, session : Session = Depends(get_session)):
#     user = session.get(User, user_id)
#     if not user: raise HTTPException(status_code=404, detail="User not found")
#     return user

def get_user(username : str, session : Session = Depends(get_session)):
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

def authenticate_user(username : str, password : str, session : Session = Depends(get_session)) -> User:
    """
    Determine if a user's login attempt is legitimate.

    Args:
        username (str): The username provided by the user.
        password (str): The plaintext password provided by the user.

    Returns:
        user (User): The User object if the user logged in successfully.
    
    Raises:
        HTTPException: A 401 (FORBIDDEN) exception is returned if the login attempt failed.
    """
    fail = HTTPException(
        status_code = 401,
        detail = "User ID or password is incorrect",
        headers = {"WWW-Authenticate": "Bearer"}
    )
    
    # If the user account does not exist, raise the same exception
    # as if the password were incorrect to prevent attackers from
    # being able to find which usernames are linked to accounts
    try:
        user = get_user(username, session)
    except: raise fail

    password_match = PasswordHasher.verify(password, user.password_hash)
    if not password_match: raise fail

    return user 

@router.post("/login/")
def login(login_form_data : Annotated[OAuth2PasswordRequestForm, Depends()], session : Session = Depends(get_session)):
    # Check the login credentials match an account. If not, raise an exception.
    user = authenticate_user(login_form_data.username, login_form_data.password, session)

    json_web_token_data = {
        "sub" : user.username,
        "exp" : datetime.now(timezone.utc) + LOGIN_SESSION_EXPIRY
    }

    token = jwt.encode(json_web_token_data, key=get_secret_key(), algorithm="HS256")

    return {
        "access_token" : token,
        "token" : token,
        "token_type" : "bearer",
        "user" : user.id
    }

@router.get("/users/self", response_model=UserPublic)
async def get_current_user(current_user : User = Depends(root_get_current_user)):
    return current_user # TODO: THIS IS BAD

# @router.get("/users/{user_id}", response_model = UserPublic)
# async def get_user_safe(user_id : int, current_user : User = Depends(get_current_user), session : Session = Depends(get_session)):
#     """
#     Obtain the User object of the current user, OR of any given user IF the current user is an administrator.
#     """
#     if not current_user.id == user_id and not current_user.admin: raise HTTPException(
#         status_code=401,
#         detail="You do not have permission to access that resource"
#     )
#     return get_user(user_id, session)

@router.post("/users/", response_model = UserPublic)
async def create_user(data : UserCreate, session : Session = Depends(get_session)):
    existing_user = session.exec(
        select(User).where(User.username == data.username)
    ).first()
    if existing_user is not None:
        raise HTTPException(
            status_code = 400,
            detail = "Username is already taken"
        )

    extra_data = {
        "password_hash" : PasswordHasher.hash(data.password)
    }
    
    if data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(data.magic, data.magic_provider) 

    user = User.model_validate(data, update = extra_data)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.patch("/users/self", response_model = UserPublic)
async def update_user(new_data : UserUpdate, user : User = Depends(get_current_user), session : Session = Depends(get_session)):
    new_data_dict = new_data.model_dump(exclude_none=True)

    extra_data = {}
    if new_data.password is not None:
        extra_data["hashed_password"] = PasswordHasher.hash(new_data.password)

    if new_data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(new_data.magic, new_data.magic_provider) 
    
    user.sqlmodel_update(new_data_dict, update=extra_data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# @router.get("/users/self/assignments")
# async def get_assignments(current_user : User = Depends(get_current_user)):
#     raise HTTPException(status_code=400, detail="Not yet implemented")
#     pass 
# 
# @router.delete("/users/{user_id}")
# def delete_user(user_id : int, session : Session = Depends(get_session)):
#     user : User = get_user(user_id, session)
#     session.delete(user)
#     session.commit()
#     return {"ok":True}

