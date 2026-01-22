from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select
from pwdlib import PasswordHash

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
    magic_hash : str

class UserCreate(UserBase):
    password : str

class UserUpdate(SQLModel):
    id : int | None
    admin : bool | None
    disabled : bool | None
    password : str | None
    magic : str | None

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
    extra_data = {"password_hash" : PasswordHash.recommended().hash(data.password)}

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
        extra_data["hashed_password"] = PasswordHash.recommended().hash(new_data.password)
    
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
