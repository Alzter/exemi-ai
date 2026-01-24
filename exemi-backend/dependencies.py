import os
from sqlmodel import Session, create_engine
from dotenv import load_dotenv
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

# Establish a connection to the database.
# TODO: Make the connection URL specified elsewhere! 
url = "mariadb+mariadbconnector://root:root@127.0.0.1:3306/exemi"
engine = create_engine(url, echo=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_engine(): return engine

def get_session():
    with Session(engine) as session:
        yield session

def get_secret_key() -> str:
    SECRET_KEY = os.environ["SECRET_KEY"]
    key : str | None = os.environ["SECRET_KEY"]
    if key is None: raise Exception("HS256 encryption/decryption key not found!")
    return key

def get_oauth2_scheme(): return oauth2_scheme
