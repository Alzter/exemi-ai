from .dependencies import get_session, get_engine
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from fastapi.middleware.cors import CORSMiddleware
from .routers import universities, users, canvas, chats, reminders 
import sys

# Enable devmode if "fastapi dev main.py" is used
DEVMODE = False
if len(sys.argv) > 1:
    if sys.argv[1] == "dev":
        DEVMODE = True

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
    lifespan = lifespan,
    root_url = "/api",
    root_path = "/api",
    docs_url="/docs" if DEVMODE else None,
    redoc_url="/redoc" if DEVMODE else None,
    openapi_url="/openapi.json" if DEVMODE else None,
)
app.include_router(universities.router)
app.include_router(users.router)
app.include_router(canvas.router)
app.include_router(chats.router)
app.include_router(reminders.router)

origins = [
    "https://www.exemi.au",
    "https://exemi.au",
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

@app.get("/")
def read_root():
    return "Exemi API is running :)"

# def get_session():
#     with Session(engine) as session:
#         yield session
#     return user 
