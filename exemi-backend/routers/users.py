from pydantic import BaseModel
from typing import Annotated
from sqlmodel import SQLModel, Session, Field, Relationship, select
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from ..dependencies import get_session, get_secret_key, get_oauth2_scheme
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
PasswordHasher = PasswordHash.recommended()
SECRET_KEY = get_secret_key()
LOGIN_SESSION_EXPIRY = timedelta(minutes=30)
router = APIRouter()
oauth2_scheme = get_oauth2_scheme()
from .magic import encrypt_magic, decrypt_magic_hash 
from ..models import User, UserCreate, UserUpdate, UserPublic, Token, TokenData

# @router.get("/users/", response_model = list[UserPublic])
def get_users(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    users = session.exec(
        select(User).offset(offset).limit(limit)
    ).all()
    return users

# @router.get("/users/{user_id}", response_model = UserPublic)
def sudo_get_user(user_id : int, session : Session = Depends(get_session)):
    user = session.get(User, user_id)
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

    # NOTE: We only use user IDs to log on, so all usernames must map to an int.
    if not username.isnumeric(): raise fail

    try:
        id = int(username)
        user = sudo_get_user(id, session)
    # If the user does not exist, raise the same exception as an incorrect password
    # so that people can't tell if it was the username or password that failed
    except HTTPException:
        raise fail
    
    password_match = PasswordHasher.verify(password, user.password_hash)
    if not password_match: raise fail

    return user 

def create_access_token(data:dict, expires_delta:timedelta=timedelta(minutes=15)) -> str:
    """
    Encode a JSON Web Token dict using encryption key SECRET_KEY and algorithm ALGORITHM.

    Args:
        data (dict): The JSON Web Token to encode. Should have key "sub" (subject) which identifies the token bearer (user).
        expires_delta (timedelta, optional): How long the access token should be valid for. Defaults to 15 minutes.

    Returns:
        token (str): An encrypted access token.
    """

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp":expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

@router.post("/token/")
def login(login_form_data : Annotated[OAuth2PasswordRequestForm, Depends()], session : Session = Depends(get_session)) -> Token:
    # Check the login credentials match an account. If not, raise an exception.
    user = authenticate_user(login_form_data.username, login_form_data.password, session)

    json_web_token_data = {
        "sub" : str(user.id),
        "exp" : datetime.now(timezone.utc) + LOGIN_SESSION_EXPIRY
    }

    token = jwt.encode(json_web_token_data, key=SECRET_KEY, algorithm="HS256")

    return Token(access_token = token, token_type = "bearer") 

# @router.post("/users/self")
async def get_current_user(token : str = Depends(oauth2_scheme), session : Session = Depends(get_session)) -> User:
    fail = HTTPException(
        status_code=401,
        detail="Please log in first",
        headers={"WWW-Authenticate":"Bearer"}
    )
    json_web_token_data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    try:
        username = json_web_token_data.get("sub")
        if username is None: raise fail
        if not username.isnumeric(): raise fail
        user_id = int(username)
        user = sudo_get_user(user_id, session)
    except: raise fail

    if user.disabled: raise fail 
    return user

async def is_admin(user : User = Depends(get_current_user)):
    if not user.admin: raise HTTPException(
        status_code=401,
        detail="You must have administrator privileges to perform this action")
    return user

@router.get("/users/{user_id}", response_model = UserPublic)
async def get_user(user_id : int, current_user : User = Depends(get_current_user), session : Session = Depends(get_session)):
    if not current_user.id == user_id and not current_user.admin: raise HTTPException(
        status_code=401,
        detail="You do not have permission to access that resource"
    )
    return sudo_get_user(user_id, session)

@router.post("/users/", response_model = UserPublic)
async def create_user(data : UserCreate, session : Session = Depends(get_session)):
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

@router.patch("/users/{user_id}", response_model = UserPublic)
async def update_user(user_id : int, new_data : UserUpdate, user : User = Depends(get_current_user), session : Session = Depends(get_session)):
    
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

# @router.delete("/users/{user_id}")
# def delete_user(user_id : int, session : Session = Depends(get_session)):
#     user : User = get_user(user_id, session)
#     session.delete(user)
#     session.commit()
#     return {"ok":True}

