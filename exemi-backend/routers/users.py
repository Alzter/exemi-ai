from ..models import User, UserCreate, UserUpdate, UserPublic, UserPublicWithUnits
from ..models import UserBiography, UserBiographyPublic, UserBiographyCreate
from ..models import University, UniversityPublic
from typing import Annotated, Literal
from sqlmodel import Session, select, desc
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
import jwt
from ..dependencies import get_current_magic, get_session, get_secret_key, encrypt_magic
from ..dependencies import get_current_user as root_get_current_user
from ..dependencies import is_magic_valid as root_is_magic_valid
from ..dependencies import create_university_if_not_exists, get_fallback_providers, get_fallback_providers_from_user
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
PasswordHasher = PasswordHash.recommended()
LOGIN_SESSION_EXPIRY = timedelta(weeks=4)
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

    fallback_universities = get_fallback_providers_from_user(current_user)

    if not university: raise HTTPException(status_code=401, detail="The current user must have a university assigned")
    valid = await root_is_magic_valid(magic=current_magic, provider=university, fallback_providers=fallback_universities)
    if not valid: raise HTTPException(status_code=401, detail="The current user's magic is not valid")
    return True

@router.post("/magic_valid_test", response_model=bool)
async def test_is_magic_valid(
    magic : str,
    university : str,
    fallback_universities : list[str] = [],
    current_user : User = Depends(root_get_current_user)
) -> Literal[True]:
    """
    Determine if any arbitrary magic is valid (ADMIN ONLY).

    Args:
        magic (str): The magic to test.
        provider (str): The name of the institution which has installed magic.
        fallback_providers (list[str], optional): A list of backup institutions in case the first one fails.

    Raises:
        HTTPException: Raises a 401 if the magic is invalid.
    
    Returns:
        Literal[True]: If magic is valid, returns True.
    """
    if not current_user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    valid = await root_is_magic_valid(magic=magic, provider=university, fallback_providers=fallback_universities)
    if not valid: raise HTTPException(status_code=401, detail="The current user's magic is not valid")
    return True

@router.get("/users/{username}", response_model = UserPublicWithUnits)
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

@router.get("/admins")
async def do_admin_accounts_exist(
    session : Session = Depends(get_session)
):
    """
    Checks if there are any existing
    administrator accounts in the database.

    Returns:
        boolean: Whether any admin accounts exist.
    """

    existing_admins = session.exec(
        select(User).where(User.admin == True)
    ).all()

    return len(existing_admins) > 0

@router.post("/users/admin", response_model = UserPublic)
async def create_admin_user(
    data : UserCreate,
    session : Session = Depends(get_session)
):
    """
    Create an administrator account without
    authorisation if no other administrator
    accounts currently exist.

    Args:
        data (UserCreate): 
            The administrator's username and plaintext password,
            and optionally their university name and magic.

    Raises:
        HTTPException:
            Raises a 400 if the username or password is blank.
            Raises a 401 if any other administrator accounts exist.
            Raises a 401 if the magic is invalid.
            Raises a 400 if magic is given without university_name.

    Returns:
        UserPublic: The created user object.
    """

    if len(data.username) == 0 or len(data.password) == 0:
        raise HTTPException(status_code=400, detail="Username or password must not be empty")
    
    existing_admins = session.exec(
        select(User).where(User.admin == True)
    ).all()

    if existing_admins:
        raise HTTPException(status_code=401, detail="Unauthorised")
    
    extra_data = {
        "password_hash" : PasswordHasher.hash(data.password),
        "admin" : True
    }
    
    fallback_providers = []

    if data.university_name is not None:
        create_university_if_not_exists(data.university_name, session=session)
        fallback_providers = get_fallback_providers(data.university_name, session=session)

    if data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(
            data.magic,
            data.university_name,
            fallback_providers=fallback_providers
        ) 

    user = User.model_validate(data, update = extra_data)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

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

    if data.university_name is not None:
        create_university_if_not_exists(data.university_name, session=session)
    
    fallback_providers = get_fallback_providers(data.university_name, session=session)

    if data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(
            data.magic,
            data.university_name,
            fallback_providers=fallback_providers
        )
    
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

    university_name = user.university_name

    if new_data.university_name is not None:
        create_university_if_not_exists(new_data.university_name, session=session)
        university_name = new_data.university_name

    fallback_providers = get_fallback_providers(university_name, session=session)

    if new_data.magic is not None:
        extra_data["magic_hash"] = await encrypt_magic(
            new_data.magic,
            university_name,
            fallback_providers=fallback_providers
        ) 
    
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

@router.get("/bio/{username}", response_model=list[UserBiographyPublic])
def get_any_user_biographies(
    username : str,
    offset : int = 0,
    limit : int = Query(default=1, le=100),
    current_user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a list of biographies for a given user
    ordered by creation date (most recent first).

    Args:
        username (str): Username of the user to obtain biographies for
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Number of items to return. Defaults to 1. Max of 100.

    Raises:
        HTTPException:
            Raises a 401 when attempting to obtain other users' biographies if the current user is not an admin.

    Returns:
        list[UserBiographyPublic]:
            List of the user's biographies.
    """
    if username != current_user.username and not current_user.admin:
        raise HTTPException(status_code=401, detail="Unauthorised")

    bios = session.exec(
        select(UserBiography)
        .join(User)
        .where(
            User.username == username 
        ).order_by(desc(UserBiography.created_at))
        .offset(offset).limit(limit)
    ).all()

    return bios

@router.get("/bio", response_model=list[UserBiographyPublic])
def get_user_biographies(
    offset : int = 0,
    limit : int = Query(default=1, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain a list of biographies for the current user
    ordered by creation date (most recent first).

    Args:
        offset (int, optional): Pagination start index. Defaults to 0.
        limit (int, optional): Number of items to return. Defaults to 1. Max of 100.

    Raises:
        HTTPException:
            Raises a 401 when attempting to obtain other users' biographies if the current user is not an admin.

    Returns:
        list[UserBiographyPublic]:
            List of the user's biographies.
    """

    return get_any_user_biographies(
        username=user.username,
        current_user=user,
        session=session,
        offset=offset,
        limit=limit
    )

    # bios = session.exec(
    #     select(UserBiography)
    #     .join(User)
    #     .where(
    #         User.username == user.username 
    #     ).order_by(desc(UserBiography.created_at))
    #     .offset(offset).limit(limit)
    # ).all()

    # return bios

@router.get("/bio_text", response_model=str)
def get_user_biography_text(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> str:
    """
    Obtain the content of the user's latest
    biography, or an empty string if none
    exist.
    """

    bios = get_user_biographies(
        user=user,
        session=session,
        offset=0,
        limit=1
    )

    if not bios: return ""
    return bios[0].content

@router.delete("/bio/{id}", response_model=Literal[True])
async def delete_user_bio(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    existing_bio = session.get(UserBiography, id)
    if not existing_bio: raise HTTPException(status_code=404, detail="Not found")
    if existing_bio.user_id != user.id: raise HTTPException(status_code=401, detail="Unauthorised")

    session.delete(existing_bio)
    session.commit()
    return True

@router.post("/bio/self", response_model=UserBiographyPublic)
async def update_user_biography(
    new_information : UserBiographyCreate,
    max_words : int = Query(default=300, limit=1000),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new biography for the current user
    which incorporates information from their
    previous biography as well as any new information
    using an LLM to combine the two into a single string.

    Args:
        new_information (UserBiographyCreate): New bio information to add.
        max_words (int): Word limit for the user's biography. Defaults to 300. Max of 1000.

    Returns:
        UserBiographyPublic: The new, updated user biography.
    """

    from ..llm_api import update_user_bio

    previous_biography = get_user_biography_text(
        user=user,
        session=session
    )

    new_biography = await update_user_bio(
        new_information=new_information.content,
        previous_biography=previous_biography,
        max_words=max_words
    )

    update = {
        "created_at" : datetime.now(timezone.utc),
        "user_id" : user.id
    }

    data = UserBiographyCreate(content=new_biography)

    bio = UserBiography.model_validate(data, update=update)

    session.add(bio)
    session.commit()
    session.refresh(bio)

    return bio
