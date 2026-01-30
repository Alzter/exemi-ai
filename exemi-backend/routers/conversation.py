from ..models import User, Conversation, ConversationCreate, ConversationPublic, ConversationPublicWithMessages, Message, MessageCreate, MessagePublic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from ..dependencies import get_current_user, get_session
from datetime import datetime, timezone
import time

router = APIRouter()

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

@router.get("/conversations/{user_id}", response_model=list[ConversationPublicWithMessages])
async def get_conversations_for_user(
    user_id : int | None = None,
    offset : int = 0, 
    limit : int = Query(default=100, limit=100),
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

@router.get("/conversations", response_model=list[ConversationPublicWithMessages])
async def get_conversations_for_self(
    offset : int = 0, 
    limit : int = Query(default=100, limit=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain all conversations for the current user.

    Returns:
        list[ConversationPublicWithMessages]: The conversations with their messages included.
    """
    return session.exec(
        select(Conversation).where(Conversation.user_id == user.id).offset(offset).limit(limit)
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

# @router.post("/message", response_model=ConversationPublicWithMessages)
async def add_message_to_conversation(
    data : MessageCreate,
    user : User,
    session : Session
):
    existing_conversation = session.get(Conversation, data.conversation_id)
    if not existing_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    message = Message.model_validate(data, update={
        "created_at" : datetime.now(timezone.utc)
    })

    session.add(message)
    session.commit()
    session.refresh(message)

    return existing_conversation

@router.post("/conversation", response_model=ConversationPublicWithMessages)
async def start_conversation(
    message_text : str,
    # data : ConversationCreate,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Create a new conversation with the LLM as the current user.
    Will return a new conversation object with a conversation ID,
    the user's message, and a response message from the LLM.

    Args:
        message_text (str): The message to send to the LLM.

    Returns:
        ConversationPublicWithMessages: The new conversation.
    """

    conversation_data = {
        "user_id" : user.id,
        "user" : user,
        "created_at" : datetime.now(timezone.utc)
    }

    conversation = Conversation.model_validate(conversation_data)

    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    if not conversation:
        raise HTTPException(status_code=500, detail="System error creating conversation!")
    
    if not conversation.id: raise HTTPException(status_code=500, detail="Error creating conversation! Contact Alexander Small")

    conversation_with_response = await continue_conversation(
        conversation_id = conversation.id,
        message_text=message_text,
        user=user,
        session=session
    )

    return conversation_with_response

@router.post("/conversation/{id}", response_model=ConversationPublicWithMessages)
async def continue_conversation(
    conversation_id : int,
    message_text : str,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Continue an existing conversation with the LLM
    by sending a new message and awaiting a new
    LLM response.

    Args:
        conversation_id (int): The ID of the existing conversation.
        message_text (str): The content of the user's message.

    Returns:
        ConversationPublicWithMessages:
            The conversation updated to include both the user and the LLM's messages.
    """
    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    message_data = MessageCreate(
        conversation_id = conversation_id,
        role="user",
        content=message_text
    )

    new_conversation = await add_message_to_conversation(
        message_data,
        user=user,
        session=session
    )
    
    # TODO: Add logic to call LLM to generate response. FIXME
    
    time.sleep(2) # Placeholder cooldown just to test client-side prediction.
    assistant_message_data = MessageCreate(
        conversation_id = conversation_id,
        role="assistant",
        content="PLACEHOLDER TEXT FOR LLM RESPONSE. HELLO WORLD!"
    )

    new_conversation = await add_message_to_conversation(
        assistant_message_data,
        user=user,
        session=session
    )

    return new_conversation

