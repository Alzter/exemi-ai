from pydantic import BaseModel, field_validator
from sqlalchemy.orm import object_session
from sqlmodel import SQLModel, Field, Relationship, Column, select
from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import TEXT
from bs4 import BeautifulSoup
import re

# Force timestamps to be UTC formatted
class UTCModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        return v

class UniversityBase(SQLModel):
    name : str = Field(primary_key=True, index=True, max_length=255)

class University(UniversityBase, table=True):
    aliases : list["UniversityAlias"] = Relationship(back_populates="university", cascade_delete=True)
    users : list["User"] = Relationship(back_populates="university")

class UniversityCreate(UniversityBase): pass

class UniversityAliasBase(SQLModel):
    name : str = Field(max_length=255)
    university_name : str | None = Field(default=None, max_length=255, index=True, foreign_key='university.name')

class UniversityAlias(UniversityAliasBase, table=True):
    __tablename__="university_alias"
    id : int | None = Field(primary_key=True, default=None)
    university : University = Relationship(back_populates="aliases")

class UniversityAliasPublic(UniversityAliasBase):
    id : int

class UniversityAliasCreate(UniversityAliasBase): pass

class UniversityAliasUpdate(SQLModel):
    name : str | None = None

class UniversityPublic(UniversityBase):
    pass

class UniversityPublicWithAliases(UniversityPublic):
    aliases : list[UniversityAliasPublic] = []

# Users to Units junction table (many to many)
class UsersUnitsBase(SQLModel):
    __tablename__ = "users_units"
    unit_id : int = Field(primary_key = True, foreign_key="unit.id")
    user_id : int = Field(primary_key = True, foreign_key="user.id", ondelete="CASCADE")
    nickname : str | None = Field(max_length=255, default=None)
    colour : str | None = Field(max_length=6, default=None)

class UsersUnits(UsersUnitsBase, table=True):
    user : "User" = Relationship(back_populates="units")
    unit : "Unit" = Relationship(back_populates="users")
    @property
    def readable_name(self) -> str:
        """
        Returns the nickname of this unit,
        if assigned, otherwise the readable
        name of the unit.
        """
        if self.unit.name == self.nickname or not self.nickname:
            return self.unit.readable_name# or self.unit.name
        else: return self.nickname

class UsersAssignments(SQLModel, UTCModel, table=True):
    __tablename__ = "users_assignments"
    assignment_id : int = Field(primary_key = True, foreign_key="assignment.id")
    user_id : int = Field(primary_key = True, foreign_key="user.id", ondelete="CASCADE")
    submitted : bool = Field(default=False)
    submitted_at : datetime | None = Field(default=None)
    extension_due_at : datetime | None = Field(default=None)
    user : "User" = Relationship(back_populates="assignments")
    assignment : "Assignment" = Relationship(back_populates = "users")

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
    units : list[UsersUnits] = Relationship(back_populates="user", cascade_delete=True)
    assignments : list[UsersAssignments] = Relationship(back_populates="user", cascade_delete=True)
    reminders : list["Reminder"] = Relationship(back_populates="user", cascade_delete=True)
    tasks : list["Task"] = Relationship(back_populates="user", cascade_delete=True)
    university : University = Relationship(back_populates="users")
    biographies : list["UserBiography"] = Relationship(back_populates="user", cascade_delete=True)
    active_university_name : str | None = Field(default=None, max_length=255, index=True)
    tasks_generation_assignments_snapshot : str | None = Field(
        default=None,
        sa_column=Column(TEXT),
        description="JSON snapshot of assignment payload at last committed task generation (no days_remaining), for LLM prompt deltas.",
    )

    @property
    def actual_university_name(self) -> str | None:
        """
        Returns the name of the university alias
        which allows access to the user's Canvas account if set,
        otherwise the user's default university name.

        The user has two fields which refer to which university
        they belong to: ``university_name`` and ``active_university_name``.

        ``university_name`` is the original name of the university the
        user is assigned to.

        ``active_university_name`` is the name of the particular
        alias of the university which was used to authenticate
        the user's Canvas account, if any.

        For example, if a student is registered under
        the university_name "swinburne" but is actually a
        "swinburneonline" student, their active_university_name
        field will be "swinburneonline".

        Returns:
            str | None: The user's university alias if set, otherwise the default university name.
        """
        return self.active_university_name or self.university_name

    @property
    def fallback_university_names(self) -> list[str]:
        """
        Returns all alias names of the user's university.
        If the user's active_university_name is set - a
        field which determines which university alias the user
        is currently using - the list of alias names will have
        this particular alias removed and the *original*
        university name added at the beginning of the list.

        Returns:
            list[str]: List of university alias names.
        """
        if not self.university: return []

        university_public = UniversityPublicWithAliases.model_validate(self.university)
        
        aliases : list[UniversityAliasPublic] = university_public.aliases
        alias_names : list[str] = [a.name for a in aliases]

        if self.active_university_name != self.university_name and self.active_university_name is not None:
            if self.active_university_name in alias_names:
                alias_names.remove(self.active_university_name)
            
            alias_names.insert(0, self.university_name)
        
        return alias_names

class UserPublic(UserBase):
    id : int
    admin : bool = False
    disabled : bool = False
    password_hash : str
    magic_hash : str | None = None
    university : UniversityPublicWithAliases | None = None
    active_university_name : str | None
    actual_university_name : str | None
    fallback_university_names : list[str]

class UserCreate(UserBase):
    password : str
    magic : str | None = None

class UserUpdate(SQLModel):
    password : str | None = None
    magic : str | None = None
    university_name : str | None = None
    active_university_name : str | None = None

class UserBiographyBase(SQLModel):
    content : str = Field(sa_column=Column(TEXT),default="")

class UserBiography(UserBiographyBase, table=True):
    __tablename__ = "user_biography"
    id : int | None = Field(primary_key=True, default=None)
    user_id : int = Field(foreign_key="user.id")
    created_at : datetime
    user : User = Relationship(back_populates="biographies")

class UserBiographyPublic(UserBiographyBase):
    id : int
    user_id : int
    created_at : datetime
    user : UserPublic

class UserBiographyCreate(UserBiographyBase):
    pass

class TermBase(SQLModel):
    university_name : str = Field(max_length=255, index=True, foreign_key='university.name')
    start_at : datetime
    end_at : datetime
    name : str = Field(max_length=255)
    canvas_id : int = Field()

class Term(TermBase, table=True):
    id : int | None = Field(primary_key=True,default=None)
    units : list["Unit"] = Relationship(back_populates="term")

class TermCreate(TermBase): pass

class TermPublic(TermBase, UTCModel):
    id : int

class TermUpdate(SQLModel):
    start_at : datetime | None = None
    end_at : datetime | None = None
    name : str | None = None

unit_name_parser = re.compile(r"(?:[A-Z0-9]+[- ][A-Z0-9]+[- ])(?:[A-Z]*\d+\/?)*[- ]?([^\(\n]*)")

class UnitBase(SQLModel):
    name : str = Field(max_length=255)
    term_id : int = Field(foreign_key="term.id")
    canvas_id : int = Field()
    # Weight final grade based on assignment group percentages
    apply_assignment_group_weights : bool
    
    @property
    def readable_name(self) -> str:
        """
            Translates SUT unit names with the format
            <YEAR>-<TERM>-<CODE(s)>-<NAME> into <NAME>.

            E.g., "2022-HS1-TNE10006/TNE60006-Networks and Switching (Semester 1)" -> "Networks and Switching"

            If regex parsing fails, just returns the original name.
        """
        if not isinstance(self.name, str):
            return str(self.name) if self.name is not None else ""

        match = unit_name_parser.search(self.name)
        if match:
            return match.group(1).strip()
        else:
            return self.name

class Unit(UnitBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    assignment_groups : list["AssignmentGroup"] = Relationship(back_populates="unit")
    term : Term = Relationship(back_populates="units")
    users : list[UsersUnits] = Relationship(back_populates="unit")

class UnitCreate(UnitBase): pass

class UnitPublic(UnitBase):
    id : int

class UnitUpdate(SQLModel):
    name : str | None = None

class TermPublicWithUnits(TermPublic):
    units : list[UnitPublic] = []

class UnitPublicWithTerm(UnitPublic):
    term : TermPublic | None = None

class UsersUnitsPublic(UsersUnitsBase):
    user : UserPublic
    unit : UnitPublicWithTerm
    readable_name : str

# class UserPublicWithUnits(UserPublic):
#     units : list[UsersUnitsPublic] = []

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

    @property
    def total_points(self) -> float:
        return sum(a.points or 0 for a in self.assignments)

class AssignmentGroupCreate(AssignmentGroupBase): pass

class AssignmentGroupUpdate(SQLModel):
    name : str | None = None
    group_weight : float | None = None

class AssignmentGroupPublic(AssignmentGroupBase):
    id : int
    total_points : float

class UnitPublicWithAssignmentGroups(UnitPublic):
    assignment_groups : list[AssignmentGroupPublic] = []

class AssignmentGroupPublicWithUnit(AssignmentGroupPublic):
    unit : UnitPublicWithTerm

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
    users : list[UsersAssignments] = Relationship(back_populates="assignment")
    tasks : list["Task"] = Relationship(back_populates="assignment")

    @property
    def readable_description(self) -> str:
        """
        By default, Canvas assignment descriptions
        consist of HTML elements. This property
        strips the HTML tags from the assignment
        description to obtain a more legible result.

        Returns:
            str: The readable assignment description.
        """
        return BeautifulSoup(
            self.description or "", "html.parser"
        ).get_text()

    @property
    def grade_contribution(self) -> float:
        """
        Calculates the assignment's contribution to the unit's final
        grade as a percentage from 0 to 1.

        If the assignment's unit does not apply assignment group
        weights, the assignment's grade contribution is given by
        the simple formula:

        assignment.contribution = (assignment.points / 100)

        Otherwise, the assignment's contribution is given by this formula:

        assignment.contribution = (assignment.points / assignment.group.total_points) * (assignment.group.group_weight / 100)

        Returns:
            float: Grade contribution.
        """

        if not self.group.unit.apply_assignment_group_weights:
            return (self.points / 100)

        if not self.group or not self.group.total_points:
            return 0.0
        return ((self.points or 0) / self.group.total_points) * (self.group.group_weight / 100)

class AssignmentCreate(AssignmentBase): pass

class AssignmentUpdate(SQLModel):
    name : str | None = None
    description : str | None = None
    due_at : datetime | None = None
    points : float | None = None

class AssignmentPublic(AssignmentBase):
    id : int
    readable_description : str
    grade_contribution : float

class AssignmentGroupPublicWithAssignments(AssignmentGroupPublic):
    assignments : list[AssignmentPublic] = []

class AssignmentPublicWithGroup(AssignmentPublic):
    group : AssignmentGroupPublic

class ConversationBase(SQLModel):
    pass

class Conversation(ConversationBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    user_id : int = Field(foreign_key='user.id', ondelete="CASCADE")
    unit_id : int | None = Field(default=None, foreign_key='unit.id', ondelete="SET NULL")
    messages : list["Message"] = Relationship(back_populates="conversation", cascade_delete=True)
    user : User = Relationship(back_populates="conversations")
    created_at : datetime
    summary : str | None = Field(sa_column=Column(TEXT),default=None)

class NewMessage(SQLModel):
    message_text : str = Field(sa_column=Column(TEXT))
    unit_id : int | None = Field(default=None, foreign_key='unit.id')

class ConversationPublic(ConversationBase, UTCModel):
    id : int
    user_id : int
    unit_id : int | None
    created_at : datetime
    summary : str | None

class ConversationUpdate(SQLModel):
    summary : str | None = None

class MessageBase(SQLModel):
    conversation_id : int = Field(foreign_key='conversation.id', ondelete="CASCADE")
    role : str = Field(max_length=30)
    content : str = Field(sa_column=Column(TEXT))

class Message(MessageBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    conversation : Conversation = Relationship(back_populates="messages")
    created_at : datetime

class MessageCreate(MessageBase): pass

class MessagePublic(MessageBase, UTCModel):
    id : int
    created_at : datetime

class MessageUpdate(SQLModel):
    content : str = Field(sa_column=Column(TEXT))

class ConversationPublicWithMessages(ConversationPublic):
    messages : list[Message] = []

class TaskBase(SQLModel):
    name : str = Field(max_length=255)
    description : str = Field(default="", sa_column=Column(TEXT))
    duration_mins : int = Field(default=15)
    assignment_id : int | None = Field(default=None, foreign_key='assignment.id', ondelete="CASCADE")
    due_at : datetime

class Task(TaskBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    created_at : datetime
    progress_mins : int = 0
    user_id : int = Field(foreign_key="user.id", ondelete="CASCADE")
    user : User = Relationship(back_populates="tasks")
    assignment : Assignment | None = Relationship(back_populates="tasks")
    completed : bool

    @property
    def colour_raw(self) -> str | None:
        """
        Obtain the colour of the task
        by obtaining the colour of the
        Unit which contains the task
        for the given User which is
        enrolled in the unit. If the
        task does not have an assignment
        given, or the Unit lacks a
        colour assigned to it by the
        user, returns None.

        Returns:
            str | None: The assignment's colour if given.
        """
        if not self.assignment: return None

        unit = self.assignment.group.unit

        session = object_session(self)

        user_unit = session.exec(
            select(UsersUnits)
            .where(UsersUnits.unit_id == unit.id)
        ).first()

        if user_unit:
            return user_unit.colour
        
        return None

class TaskCreate(TaskBase): pass

class TaskUpdate(SQLModel):
    name : str | None = None
    description : str | None = None
    duration_mins : int | None = None
    progress_mins : int | None = None
    assignment_id : int | None = None
    due_at : datetime | None = None
    completed : bool | None = None

class TaskPublic(TaskBase, UTCModel):
    id : int
    created_at : datetime
    user_id : int
    user : UserPublic
    assignment : AssignmentPublic | None = None
    progress_mins : int
    colour_raw : str | None = None

class TaskLLM(BaseModel):
    id : int | None
    assignment_id : int
    name : str
    description : str
    duration_mins : int
    due_at : datetime
    completed : bool

class TaskList(BaseModel):
    tasks : list[TaskLLM]

class ReminderBase(SQLModel):
    # canvas_assignment_id : int
    assignment_name : str = Field(max_length=255)
    description : str = Field(sa_column=Column(TEXT))
    due_at : datetime

class Reminder(ReminderBase, table=True):
    id : int | None = Field(primary_key=True, default=None)
    created_at : datetime
    user_id : int = Field(foreign_key="user.id", ondelete="CASCADE")
    user : User = Relationship(back_populates="reminders")

class ReminderPublic(ReminderBase, UTCModel):
    id : int
    created_at : datetime
    user_id : int

class ReminderCreate(ReminderBase): pass

class ReminderUpdate(SQLModel):
    # canvas_assignment_id : int | None = None
    assignment_name : str | None = None
    description : str | None = Field(sa_column=Column(TEXT), default=None)
    due_at : datetime | None = None
