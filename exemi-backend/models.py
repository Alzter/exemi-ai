from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship

class Token(BaseModel):
    access_token : str
    token_type : str

class TokenData(BaseModel):
    username : str | None = None

class UserBase(SQLModel):
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

