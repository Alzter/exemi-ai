from ..models import User, UserCreate, UserUpdate, UserPublic
from typing import Annotated, Literal
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from ..dependencies import get_current_magic, get_session, get_secret_key, encrypt_magic
from ..dependencies import get_current_user as root_get_current_user
from ..dependencies import is_magic_valid as root_is_magic_valid
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
PasswordHasher = PasswordHash.recommended()
LOGIN_SESSION_EXPIRY = timedelta(minutes=30)
router = APIRouter()

@router.get("/users", response_model = list[UserPublic])
def get_users(
    offset : int = 0,
    limit : int = Query(default=100, le=100),
    current_user : User = Depends(root_get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a list of user accounts (ADMIN ONLY).

    Args:
        offset (int): Pagination start index.
        limit (int): Page length. Maximum of 100.
    
    Raises:
        HTTPException: Raises a 401 if the current user is not an admin.

    Returns:
        List[UserPublic]: The accounts.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    users = session.exec(
        select(User).offset(offset).limit(limit)
    ).all()
    return users

# def get_user_by_id_unsafe(
#     user_id : int,
#     session : Session = Depends(get_session)
# ):
#     user = session.get(User, user_id)
#     if not user: raise HTTPException(status_code=404, detail="User not found")
#     return user

def get_user_unsafe(
    username : str,
    session : Session = Depends(get_session)
) -> User:
    """
    Find a user by username.
    NOTE: This should NOT be exposed as an API
    endpoint, as it can be called without admin
    privileges! Use get_user_safe() instead.

    Args:
        username (str): The username to find the user.

    Returns:
        User: The user object. Note that this is NOT parsed into a UserPublic.
    """
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def authenticate_user(
    username : str,
    password : str,
    session : Session = Depends(get_session)
) -> User:
    """
    Determine if a user's login attempt is legitimate.

    Args:
        username (str): The username provided by the user.
        password (str): The plaintext password provided by the user.

    Raises:
        HTTPException: A 401 exception is returned if the login attempt failed.

    Returns:
        user (User): The User object if the user logged in successfully.
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
        user = get_user_unsafe(username, session)
    except: raise fail

    password_match = PasswordHasher.verify(password, user.password_hash)
    if not password_match: raise fail

    return user 

@router.post("/login")
def login(
    login_form_data : Annotated[OAuth2PasswordRequestForm, Depends()],
    session : Session = Depends(get_session)
) -> dict:
    """
    Authorise a user and return a JSON web token
    if their login credentials are legitimate.

    Args:
        login_form_data (OAuth2PasswordRequestForm):
            A login form with a username and password.
    
    Raises:
        HTTPException:
            Raises a 401 if the login attempt was not legitimate.

    Returns:
        dict: The user's JSON web token.
    """
    # Check the login credentials match an account. If not, raise an exception.
    user = authenticate_user(login_form_data.username, login_form_data.password, session)

    json_web_token_data = {
        "sub" : user.username,
        "exp" : datetime.now(timezone.utc) + LOGIN_SESSION_EXPIRY
    }

    token = jwt.encode(json_web_token_data, key=get_secret_key(), algorithm="HS256")

    return {
        "access_token" : token,
        "token_type" : "bearer",
        "user_id" : user.id,
        "user" : user
    }

@router.get("/users/self", response_model=UserPublic)
async def get_current_user(current_user : User = Depends(root_get_current_user)):
    """
    Obtain a UserPublic object representing the logged in user.
    """
    return current_user

@router.get("/magic_valid", response_model=bool)
async def is_magic_valid(
    current_magic : str = Depends(get_current_magic),
    current_user : User = Depends(root_get_current_user)
) -> Literal[True]:
    """
    Determine if the user's current magic is valid.
    Returns 200 response if the magic is valid, else 401.

    Raises:
        HTTPException: Raises a 401 if the magic is invalid.
    
    Returns:
        Literal[True]: If magic is valid, returns True.
    """
    university = current_user.university_name
    if not university: raise HTTPException(status_code=401, detail="The current user must have a university assigned")
    valid = await root_is_magic_valid(magic=current_magic, provider=university)
    if not valid: raise HTTPException(status_code=401, detail="The current user's magic is not valid")
    return True

@router.get("/users/{username}", response_model = UserPublic)
async def get_user_safe(
    username : str,
    current_user : User = Depends(root_get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a UserPublic object representing a given
    user, ONLY if the user is an admin or the user
    is the same user as the one being requested.

    Args:
        username (str): The username of the user to find.

    Raises:
        HTTPException:
            Raises a 401 if the user retrieved is not the current user and the current user is not an admin.

    Returns:
        UserPublic: The user object.
    """
    if not current_user.username == username and not current_user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")
    return get_user_unsafe(username, session)

@router.post("/users", response_model = UserPublic)
async def create_user(
    data : UserCreate,
    current_user : User = Depends(root_get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new user account (ADMIN ONLY).

    Args:
        data (UserCreate): 
            The user's username and plaintext password,
            and optionally their university name and magic.

    Raises:
        HTTPException:
            Raises a 401 if the current user is not an admin.
            Raises a 400 if the username is already taken.
            Raises a 401 if the magic is invalid.
            Raises a 400 if magic is given without university_name.

    Returns:
        UserPublic: The created user object.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    
    if len(data.username) == 0 or len(data.password) == 0:
        raise HTTPException(status_code=400, detail="Username or password must not be empty")

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
        extra_data["magic_hash"] = await encrypt_magic(data.magic, data.university_name) 

    user = User.model_validate(data, update = extra_data)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.patch("/users/self", response_model = UserPublic)
async def update_user(
    new_data : UserUpdate,
    user : User = Depends(root_get_current_user),
    session : Session = Depends(get_session)
):
    """
    Change the account details of the currently logged in user.

    Args:
        new_data (UserUpdate): Changes to the user's password, university name, and/or magic.

    Raises:
        HTTPException:
            Raises a 401 if the magic is invalid.
            Raises a 400 if magic is given without university_name.
    
    Returns:
        UserPublic: The modified user object.
    """
    new_data_dict = new_data.model_dump(exclude_none=True)

    extra_data = {}
    if new_data.password is not None:
        extra_data["password_hash"] = PasswordHasher.hash(new_data.password)

    if new_data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(new_data.magic, new_data.university_name) 
    
    user.sqlmodel_update(new_data_dict, update=extra_data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.delete("/users/{username}")
def delete_user(
    username : str,
    current_user : User = Depends(root_get_current_user),
    session : Session = Depends(get_session)
) -> Literal[True]:
    """
    Delete a user account (ADMIN ONLY).

    Args:
        username (str): Name of the user account to delete.

    Raises:
        HTTPException: Raises a 401 if the current user is not an admin.

    Returns:
        Literal[True]: Returns True if the user was deleted successfully.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    user : User = get_user_unsafe(username, session)
    session.delete(user)
    session.commit()
    return True 

