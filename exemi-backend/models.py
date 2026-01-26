from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

class Token(BaseModel):
    access_token : str
    token_type : str

class TokenData(BaseModel):
    username : str | None = None

class UserBase(SQLModel):
    username : str = Field(max_length=255, unique=True)
    magic_provider : str | None = Field(default=None, max_length=255, index=True)

class User(UserBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    admin : bool = Field(default = False)
    disabled : bool = Field(default=False)
    password_hash : str = Field(max_length=255)
    magic_hash : str | None = Field(default=None, max_length=255)

class UserPublic(UserBase):
    id : int
    admin : bool = False
    disabled : bool = False
    password_hash : str
    magic_hash : str | None = None

class UserCreate(UserBase):
    password : str
    magic : str | None = None

class UserUpdate(SQLModel):
    password : str | None = None
    magic : str | None = None
    magic_provider : str | None = None
class UnitBase(SQLModel):
    name : str = Field(max_length=255)
    start_at : datetime = Field()
    end_at : datetime = Field() 

class Unit(SQLModel, table=True):
    id : int | None = Field(primary_key=True, default=None)
    assignments : list["Assignment"] = Relationship(back_populates="unit")

class UnitPublic(UnitBase):
    id : int 

class AssignmentBase(SQLModel):
    unit_id : int | None = Field(default=None, foreign_key="unit.id")
    name : str = Field(max_length=255)
    description : str = Field(max_length=2048)
    due_at : datetime = Field()
    points : int = Field()
    is_group : bool = Field()

class Assignment(AssignmentBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    unit : Unit | None = Relationship(back_populates="assignments")

class AssignmentPublic(AssignmentBase):
    id : int

