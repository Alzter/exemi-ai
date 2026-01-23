import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from pwdlib import PasswordHash
import jwt
from dotenv import load_dotenv
PasswordHasher = PasswordHash.recommended()
# Used for HS256 symmetric encryption of user tokens.
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None: raise Exception("JSON Web Token HS256 symmetric encryption key not found from .env file!")
LOGIN_SESSION_EXPIRY = timedelta(minutes=30)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token : str
    token_type : str

class UserBase(SQLModel):
    admin : bool = Field(default=False)
    disabled : bool = Field(default=False)

class User(UserBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    password_hash : str = Field(max_length=255)
    magic_hash : str | None = Field(default=None, max_length=255)

class UserPublic(UserBase):
    id : int
    password_hash : str
    magic_hash : str | None = None

class UserCreate(UserBase):
    password : str
    magic : str | None = None

class UserUpdate(SQLModel):
    id : int | None = None
    admin : bool | None = None
    disabled : bool | None = None
    password : str | None = None
    magic : str | None = None

# Establish a connection to the database.
# TODO: Make the connection URL specified elsewhere! 
url = "mariadb+mariadbconnector://root:root@127.0.0.1:3306/exemi"
engine = create_engine(url, echo=True)

def create_db_and_tables():
    # TODO: This does not update table schemas after
    # they are initially created!
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app : FastAPI):
    # Startup
    create_db_and_tables()
    yield
    # Shutdown

app = FastAPI(lifespan = lifespan)

def get_session():
    with Session(engine) as session:
        yield session

@app.post("/users/", response_model = UserPublic)
def create_user(data : UserCreate, session : Session = Depends(get_session)):

    extra_data = {
        "password_hash" : PasswordHasher.hash(data.password)
    }
    
    # TODO: Implement magic encryption at rest
    if data.magic is not None: extra_data["magic_hash"] = data.magic

    user = User.model_validate(data, update = extra_data)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/users/", response_model = list[UserPublic])
def get_users(offset : int = 0, limit : int = Query(default=100, limit=100), session : Session = Depends(get_session)):
    users = session.exec(
        select(User).offset(offset).limit(limit)
    ).all()
    return users

@app.get("/users/{user_id}", response_model = UserPublic)
def get_user(user_id : int, session : Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user: raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{user_id}", response_model = UserPublic)
def update_user(user_id : int, new_data : UserUpdate, session : Session = Depends(get_session)):
    user : User = get_user(user_id, session)
    new_data_dict = new_data.model_dump(exclude_none=True)
    
    extra_data = {}
    if new_data.password is not None:
        extra_data["hashed_password"] = PasswordHasher.hash(new_data.password)

    # TODO: Encrypt magic at rest!
    if new_data.magic is not None:
        extra_data["magic_hash"] = new_data.magic
    
    user.sqlmodel_update(new_data_dict, update=extra_data)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id : int, session : Session = Depends(get_session)):
    user : User = get_user(user_id, session)
    session.delete(user)
    session.commit()
    return {"ok":True}

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
        user = get_user(id, session)
    # If the user does not exist, raise the same exception as an incorrect password
    # so that people can't tell if it was the username or password that failed
    except HTTPException:
        raise fail
    
    password_match = PasswordHasher.verify(password, user.password_hash)
    if not password_match: raise fail

    return user 

@app.post("/token/")
def login(login_form_data : Annotated[OAuth2PasswordRequestForm, Depends()], session : Session = Depends(get_session)) -> str:
    # Check the login credentials match an account. If not, raise an exception.
    authenticate_user(login_form_data.username, login_form_data.password, session)

    json_web_token_data = {
        "sub" : login_form_data.username,
        "exp" : datetime.now(timezone.utc) + LOGIN_SESSION_EXPIRY
    }

    token = jwt.encode(json_web_token_data, key=SECRET_KEY, algorithm="HS256")
    
    return token

async def get_current_user(token : str = Depends(oauth2_scheme), session : Session = Depends(get_session)) -> User:
    fail = HTTPException(
        status_code=401,
        detail="Please log in first",
        headers={"WWW-Authenticate":"Bearer"}
    )
    try:
        json_web_token_data = jwt.decode(token, SECRET_KEY, algorithms="HS256")
        username = json_web_token_data.get("sub")
        if username is None: raise fail 
    except: raise fail 
    
    if not username.isnumeric(): raise fail
    user_id = int(username)

    user = get_user(user_id, session)
    if user.disabled: raise HTTPException(status_code=400, detail="User is disabled")
    return user

async def is_admin(user : User = Depends(get_current_user)):
    if not user.admin: raise HTTPException(
        status_code=401,
        detail="You must have administrator privileges to perform this action")
    return user
