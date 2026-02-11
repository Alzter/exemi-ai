from .dependencies import get_session, get_engine
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from fastapi.middleware.cors import CORSMiddleware
from .routers import universities, users, canvas, chats 

# # Establish a connection to the database.
# # TODO: Make the connection URL specified elsewhere! 
# url = "mariadb+mariadbconnector://root:root@127.0.0.1:3306/exemi"
# engine = create_engine(url, echo=True)

def create_db_and_tables(engine = get_engine()):
    # TODO: This does not update table schemas after
    # they are initially created!
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app : FastAPI):
    # Startup
    create_db_and_tables()
    yield
    # Shutdown

app = FastAPI(
    lifespan = lifespan
    root_url = "/api",
    root_path = "/api"
)
app.include_router(universities.router)
app.include_router(users.router)
app.include_router(canvas.router)
app.include_router(chats.router)

origins = [
    "https://www.exemi.au",
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

# def get_session():
#     with Session(engine) as session:
#         yield session
#     return user 

