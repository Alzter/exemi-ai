from ..models import User, Conversation, ConversationCreate, ConversationPublic, ConversationPublicWithMessages, Message, MessageCreate, MessagePublic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from ..dependencies import get_current_user, get_session
from datetime import datetime, timezone

router = APIRouter()

@router.post("/conversation", response_model=ConversationPublic)
async def create_conversation(
    # data : ConversationCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new conversation as the current user.
    """

    data = {
        "user_id" : user.id,
        "user" : user,
        "created_at" : datetime.now(timezone.utc)
    }

    conversation = Conversation.model_validate(data)

    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation

@router.get("/conversation/{id}", response_model=ConversationPublicWithMessages)
async def get_conversation(id : int, user : User = Depends(get_current_user), session : Session = Depends(get_session)):
    """
    Obtain an existing conversation with its messages.

    Args:
        id (int): The ID of the conversation to retrieve.
    
    Raises:
        HTTPException:
            If the current user is not an administrator, this will return a 401 (Unauthorized) response when attempting to view other users' conversations.
            This will also return a 404 (not found) if the conversation did not exist in the DB.
    
    Returns:
        ConversationPublicWithMessages: The conversation with its messages included.
    """

    conversation = session.get(Conversation, id)

    if not conversation: raise HTTPException(status_code=404, detail=f"Conversation not found with ID {id}")

    if not conversation.user_id == user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to view this conversation")

    return conversation

@router.get("/conversations", response_model=list[ConversationPublicWithMessages])
async def get_conversations(
    offset : int = 0, 
    limit : int = Query(default=100, limit=100),
    user_id : int | None = None,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain all conversations for a given user.

    Args:
        user_id (int, optional): The ID of the user who created the conversation. Defaults to the current user's ID.
    
    Raises:
        HTTPException:
            If the current user is not an administrator, this will return a 401 (Unauthorized) response when attempting to view other users' conversations.

    Returns:
        list[ConversationPublicWithMessages]: The conversations with their messages included.
    """
    if user_id is None: user_id = user.id
    if user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to view these conversations")

    return session.exec(
        select(Conversation).where(Conversation.user_id == user_id).offset(offset).limit(limit)
    ).all()

@router.delete("/conversation/{id}")
async def delete_conversation(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Deletes a conversation for a given user, provided that the current user is an administrator.

    Args:
        id (int): The ID of the conversation to delete.

    Raises:
        HTTPException: Returns a 401 if the user is not an administrator.
    
    Returns:
        dict: Successful response {"ok":True}.
    """
    if not user.admin: raise HTTPException(status_code=401, detail="You are not authorised to delete this conversation")
    conversation = session.exec(select(Conversation, id)).first()
    if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")

    session.delete(conversation)
    session.commit()
    return {"ok" : True}

@router.post("/message", response_model=MessagePublic)
async def create_message(
    data : MessageCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    existing_conversation = session.get(Conversation, data.conversation_id)
    if not existing_conversation:
        raise HTTPException(status_code=400, detail="Conversation ID does not match an existing conversation")
    
    message = Message.model_validate(data, update={
        "created_at" : datetime.now(timezone.utc)
    })

    session.add(message)
    session.commit()
    session.refresh(message)
    return message

