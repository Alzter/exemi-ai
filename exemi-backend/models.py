from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column
from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import TEXT, LONGTEXT

class University(SQLModel, table=True):
    name : str = Field(primary_key=True, index=True, max_length=255)

class UserBase(SQLModel):
    username : str = Field(max_length=255, unique=True)
    university_name : str | None = Field(default=None, max_length=255, index=True, foreign_key='university.name', ondelete="SET NULL")

class User(UserBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    admin : bool = Field(default = False)
    disabled : bool = Field(default=False)
    password_hash : str = Field(max_length=255)
    magic_hash : str | None = Field(default=None, max_length=255)
    conversations : list["Conversation"] = Relationship(back_populates="user", cascade_delete=True)

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
    university_name : str | None = None

class TermBase(SQLModel):
    start_at : datetime
    end_at : datetime
    name : str = Field(max_length=255, unique=True)
    university_name : str = Field(max_length=255, index=True, foreign_key='university.name')
    canvas_id : int = Field()

class Term(TermBase, table=True):
    id : int | None = Field(primary_key=True,default=None)
    units : list["Unit"] = Relationship(back_populates="term")

class TermCreate(TermBase): pass

class TermPublic(TermBase):
    id : int

class UnitBase(SQLModel):
    #university : str = Field(primary_key=True, index=True, max_length=255, foreign_key="university.name")
    name : str = Field(max_length=255, unique=True)
    term_id : int | None = Field(default=None, foreign_key="term.id")
    canvas_id : int = Field()
    canvas_term_id : int = Field()

class Unit(UnitBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    assignments : list["Assignment"] = Relationship(back_populates="unit")
    term : Term | None = Relationship(back_populates="units")

class UnitCreate(UnitBase): pass

class UnitPublic(UnitBase):
    id : int

class AssignmentBase(SQLModel):
    unit_id : int | None = Field(default=None, foreign_key="unit.id")
    name : str | None = Field(max_length=255, default=None)
    description : str = Field(sa_column=Column(TEXT),default="")
    due_at : datetime | None = Field(default=None)
    points : int = Field()
    is_group : bool = Field()
    canvas_id : int = Field()

class Assignment(AssignmentBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    unit : Unit | None = Relationship(back_populates="assignments")

class AssignmentCreate(AssignmentBase): pass

class AssignmentPublic(AssignmentBase):
    id : int

class ConversationBase(SQLModel):
    pass

class Conversation(ConversationBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    user_id : int = Field(foreign_key='user.id', ondelete="CASCADE")
    messages : list["Message"] = Relationship(back_populates="conversation", cascade_delete=True)
    user : User = Relationship(back_populates="conversations")
    created_at : datetime
    summary : str | None = Field(sa_column=Column(TEXT),default=None)

class ConversationCreate(ConversationBase): pass

class ConversationPublic(ConversationBase):
    id : int
    user_id : int
    created_at : datetime

class MessageBase(SQLModel):
    conversation_id : int = Field(foreign_key='conversation.id', ondelete="CASCADE")
    role : str = Field(max_length=30)
    content : str = Field(sa_column=Column(TEXT))

class Message(MessageBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    conversation : Conversation = Relationship(back_populates="messages")
    created_at : datetime

class MessageCreate(MessageBase): pass

class MessagePublic(MessageBase):
    id : int
    created_at : datetime

class ConversationPublicWithMessages(ConversationPublic):
    messages : list[Message] = []
