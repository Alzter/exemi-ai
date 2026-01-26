from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

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

class University(SQLModel, table=True):
    name : str = Field(primary_key=True, index=True, max_length=255)

class TermBase(SQLModel):
    start_at : datetime
    end_at : datetime
    name : str = Field(max_length=255)

class Term(TermBase, table=True):
    id : int | None = Field(primary_key=True,default=None)

class TermPublic(TermBase): id : int

class UnitBase(SQLModel):
    #university : str = Field(primary_key=True, index=True, max_length=255, foreign_key="university.name")
    name : str = Field(max_length=255)

class Unit(UnitBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    assignments : list["Assignment"] = Relationship(back_populates="unit")

class UnitPublic(UnitBase): id : int 

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

