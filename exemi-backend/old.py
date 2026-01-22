import requests, httpx
from copy import copy

from typing import Union, Annotated

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlmodel import Field, Session, SQLModel, create_engine, select

# Password hashing hard-coded parameters.
# This defines an Argon2 password hashing algorithm
# which we use to permanently encrypt passwords.
# TODO: how do we change the key pair for hashing?
from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()

# JSON Web Token hard-coded parameters.
# These parameters are used to sign JSON Web Tokens
# so that we can validate access tokens as being
# legitimately sent by us. This prevents attackers
# from forging access tokens to our accounts to
# breach our system.
SECRET_KEY = "3be8f0c5dc7c22f135e283712251937d8f0aae7900310c9e47077ad4c4190737"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "1" : {
        "username":"1",
        "hashed_password":password_hash.hash("abc"), # NOTE: this is insecure! Never leave a plaintext password anywhere it can be read. The point of hashing is to NEVER store plaintext passwords.
        "disabled":False
        },
    "2": {
        "username":"2",
        "hashed_password":"fakehasheddef",
        "disabled":True
        }
}

class Token(BaseModel):
    access_token : str
    token_type : str

class TokenData(BaseModel):
    username : str | None = None

class User(SQLModel, table=True):
    username: str 
    canvas_token : str | None = None
    disabled : bool | None = None
    hashed_password : str

# Identical class to User, only hashed_password is mandatory.
class UserInDB(User):
    hashed_password: str

class Message(BaseModel):
    role : str
    content : str
    timestamp : datetime

class Conversation(BaseModel):
    messages : list[Message]
    user : User
    timestamp : datetime

def verify_password(plain_password, hashed_password) -> bool:
    """
    Wrapper for password_hash.verify(), where password_hash is an instance of PasswordHash.recommended().
    Determines if a plaintext password matches a password hash.
    """
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Wrapper for password_hash.hash(), where password_hash is an instance of PasswordHash.recommended().
    Creates a hash for a given password.
    """
    return password_hash.hash(password)

def get_user(db, username : str) -> UserInDB | None:
    """
    Obtain a user from the database of users if they exist.

    Args:
        db (dict): Database of users.
        username (str): The given username.
    
    Returns:
        result (UserInDB | None): Returns the user object if they exist, else None.
    """
    if username in db:
        user_dict = db[username]
        # Create a UserInDB class using fields from user_dict.
        # This will bork if required fields are missing!!!
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username:str, password:str) -> UserInDB | bool:
    """
    Determine if a user's login attempt is legitimate.
    Args:
        fake_db (dict): Database of accounts, where each account has a username and hashed_password field.
        username (str): The username provided by the user.
        password (str): The plaintext password provided by the user.

    Returns:
        result (UserInDB | bool): Returns False if authentication failed, otherwise returns the user object.
    """

    user = get_user(fake_db, username)
    if not user: return False
    if not verify_password(password, user.hashed_password): return False
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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token : Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    Get the object of the current authenticated user if one exists,
    otherwise return a 401 (Unauthorized) response.

    Args:
        token (str): The current access token.
    
    Returns:
        user (UserInDB): The current user who is logged in.
    
    Raises:
        HTTPException: The user is not logged in, OR the user account is illegal. 
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate user credentials",
        headers={"WWW-Authenticate":"Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None: raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError: raise credentials_exception
    
    if token_data.username is None: raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None: raise credentials_exception
    return user

async def get_current_active_user(current_user : Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@app.get("/users/me")
async def read_users_me(current_user : Annotated[User, Depends(get_current_active_user)]):
    return current_user

@app.get("/items/")
async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/is_token_valid/")
async def is_token_valid(provider : str, access_token : str) -> bool:
    """
    Verify whether a manual Canvas API token generated by a user is valid for a given Canvas installation.

    Args:
        provider (str): The name of the institution which has installed Canvas.
        access_token (str): A manually generated Canvas access token.

    Returns:
        exists (bool): Returns true if the user's access token is valid for the given Canvas provider.
    """
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(f"https://{provider}.instructure.com/api/v1/users/self", params={
        "access_token":access_token,
        })
    return response.status_code == 200

@app.post("/token")
async def login_for_access_token(form_data : Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """
    Handle a user login attempt, returning an access token if the credentials were valid
    and a 401 Unauthorized response if they were not.

    Args:
        form_data (OAuth2PasswordRequestForm):
            A login attempt with two fields: 'username' and 'password'.
    
    Returns:
        token (Token): The user's access token if the login was successful.
    
    Raises:
        HTTPException: Raises 401 (Unauthorized) if login credentials were invalid.
    """


    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user: # authenticate_user will return False if login attempt is invalid, hence the falsy check here.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data = {"sub" : user.username}, expires_delta=access_token_expires
    )
    return Token(access_token = access_token, token_type="bearer")


@app.post("/chat_start/")
async def chat_start(user : Annotated[User, Depends(get_current_active_user)]):
    """
    Create a new conversation between a user and the assistant.
    """
    return Conversation(
        messages = [],
        user=user,
        timestamp=datetime.now()
    )

def chat_add(conversation : Conversation, new_message : Message) -> Conversation:
    """
    Append a new message to an existing Conversation.
    """
    return conversation.model_copy(
        update={
            "messages": [*conversation.messages, new_message]
        }
    ) 

@app.post("/chat/")
async def chat(conversation : Conversation, query : str):
    """
    For a given conversation, add a user query and then generate an LLM response.
    """

    user_message = Message(role="user",content=query,timestamp=datetime.now())

    new_conversation = chat_add(conversation, user_message)

    assistant_message = Message(role="assistant",content="Hello! This is a placeholder!", timestamp=datetime.now())

    new_conversation = chat_add(new_conversation, assistant_message)

    return new_conversation

# @app.post("/login/")
# async def login(credentials:dict):
# 
#     provider = credentials["provider"]
#     access_token = credentials["token"]
# 
#     legit = await is_token_valid(provider, access_token)
# 
#     print(legit)
# 
#     if not legit:
#         return HTTPException(status_code = 401, detail=f"Canvas access token for {provider} installation is invalid.")
#     
#     return "Authorised"
