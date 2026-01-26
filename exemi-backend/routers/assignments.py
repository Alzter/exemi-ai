from ..models import User, UserCreate, UserUpdate, UserPublic, Token
from typing import Annotated
from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_session, get_secret_key, get_current_user, get_current_magic

router = APIRouter()


