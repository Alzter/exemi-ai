from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column
from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import TEXT, LONGTEXT

class University(SQLModel, table=True):
    name : str = Field(primary_key=True, index=True, max_length=255)

# Users to Units junction table (many to many)
class UsersUnits(SQLModel, table=True):
    __tablename__ = "users_units"
    unit_id : int = Field(primary_key = True, foreign_key="unit.id")
    user_id : int = Field(primary_key = True, foreign_key="user.id")

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
    units : list["Unit"] = Relationship(back_populates="users", link_model=UsersUnits)

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
    university_name : str = Field(max_length=255, index=True, foreign_key='university.name')
    start_at : datetime
    end_at : datetime
    name : str = Field(max_length=255, unique=True)
    canvas_id : int = Field()

class Term(TermBase, table=True):
    id : int | None = Field(primary_key=True,default=None)
    units : list["Unit"] = Relationship(back_populates="term")

class TermCreate(TermBase): pass

class TermPublic(TermBase):
    id : int

class TermUpdate(SQLModel):
    start_at : datetime | None = None
    end_at : datetime | None = None
    name : str | None = None

class UnitBase(SQLModel):
    name : str = Field(max_length=255, unique=True)
    term_id : int = Field(foreign_key="term.id")
    canvas_id : int = Field()

class Unit(UnitBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    assignment_groups : list["AssignmentGroup"] = Relationship(back_populates="unit")
    term : Term = Relationship(back_populates="units")
    users : list[User] = Relationship(back_populates="units", link_model=UsersUnits)

class UnitCreate(UnitBase): pass

class UnitPublic(UnitBase):
    id : int

class UnitUpdate(SQLModel):
    name : str | None = None

class TermPublicWithUnits(TermPublic):
    units : list[Unit] = []

class UnitPublicWithTerm(UnitPublic):
    term : TermPublic | None = None

class AssignmentGroupBase(SQLModel):
    unit_id : int = Field(foreign_key="unit.id")
    name : str | None = Field(max_length=255, default=None)
    group_weight : float
    canvas_id : int = Field()

class AssignmentGroup(AssignmentGroupBase, table=True):
    __tablename__ = "assignment_group"
    id : int | None = Field(primary_key=True, default=None)
    unit : Unit = Relationship(back_populates="assignment_groups")
    assignments : list["Assignment"] = Relationship(back_populates="group")

class AssignmentGroupCreate(AssignmentGroupBase): pass

class AssignmentGroupPublic(AssignmentGroupBase):
    id : int

class AssignmentGroupUpdate(SQLModel):
    name : str | None = None
    group_weight : float | None = None

class UnitPublicWithAssignmentGroups(UnitPublic):
    assignment_groups : list[AssignmentGroupPublic] = []

class AssignmentGroupPublicWithUnit(AssignmentGroupPublic):
    unit : UnitPublic

class AssignmentBase(SQLModel):
    group_id : int = Field(foreign_key="assignment_group.id")
    canvas_id : int = Field()
    name : str | None = Field(max_length=255, default=None)
    description : str = Field(sa_column=Column(TEXT),default="")
    due_at : datetime | None = Field(default=None)
    points : float = Field(default=0)
    is_group : bool = Field()

class Assignment(AssignmentBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    group : AssignmentGroup | None = Relationship(back_populates="assignments")

class AssignmentCreate(AssignmentBase): pass

class AssignmentPublic(AssignmentBase):
    id : int

class AssignmentUpdate(SQLModel):
    name : str | None = None
    description : str | None = None
    due_at : datetime | None = None
    points : float | None = None

class AssignmentGroupPublicWithAssignments(AssignmentGroupPublic):
    assignments : list[AssignmentPublic] = []

class AssignmentPublicWithGroup(AssignmentPublic):
    group : AssignmentGroupPublic

class ConversationBase(SQLModel):
    pass

class Conversation(ConversationBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    user_id : int = Field(foreign_key='user.id', ondelete="CASCADE")
    messages : list["Message"] = Relationship(back_populates="conversation", cascade_delete=True)
    user : User = Relationship(back_populates="conversations")
    created_at : datetime
    summary : str | None = Field(sa_column=Column(TEXT),default=None)

class NewMessage(SQLModel):
    message_text : str = Field(sa_column=Column(TEXT))

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

class MessageUpdate(SQLModel):
    content : str = Field(sa_column=Column(TEXT))

class ConversationPublicWithMessages(ConversationPublic):
    messages : list[Message] = []
