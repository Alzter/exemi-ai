from ..models import User, Conversation, NewMessage, ConversationPublic, ConversationPublicWithMessages, Message, MessageCreate, MessagePublic, MessageUpdate
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, desc
from ..dependencies import get_current_magic, get_current_user, get_session
from ..llm_api import chat, chat_stream
from langchain_core.messages import BaseMessage
from datetime import datetime, timezone
from typing import Literal, AsyncGenerator
import time

router = APIRouter()

@router.get("/test_chat/{message}")
async def test_chat(
    message : str,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
) -> list[BaseMessage]:
    """
    Test the chat functionality of the LLM (ADMIN ONLY).

    Args:
        message (str): Message text to send to the LLM.

    Raises:
        HTTPException: Raises a 401 if the current user is not an admin.

    Returns:
        str: The LLM's response.
    """
    if not user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    messages = [{"role":"user","content":message}]
    response_messages : list[BaseMessage] = await chat(
        user=user,
        magic=magic,
        session=session,
        messages=messages
    )
    return response_messages

@router.get("/test_stream_chat/{message}")
async def test_chat_stream(
    message : str,
    background_tasks : BackgroundTasks,
    end_function = None,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
) -> StreamingResponse:
    """
    Test the chat functionality of the LLM using a streaming response (ADMIN ONLY).

    Args:
        message (str): Message text to send to the LLM.

    Raises:
        HTTPException: Raises a 401 if the current user is not an admin.

    Yields:
        str: The LLM's response as chunks.
    """
    if not user.admin: raise HTTPException(status_code=401, detail="Unauthorised")
    messages = [{"role":"user","content":message}]

    return StreamingResponse(
        chat_stream(
            user=user,
            magic=magic,
            session=session,
            messages=messages,
            background_tasks=background_tasks
        ),
        media_type="text/plain"
    )

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

@router.get("/conversations/{username}", response_model=list[ConversationPublic])
async def get_conversations_for_user(
    username : str | None = None,
    offset : int = 0, 
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain all conversations for a given user.

    Args:
        username (str, optional): The name of the user who created the conversation. Defaults to the current user's name.
    
    Raises:
        HTTPException:
            If the current user is not an administrator, this will return a 401 (Unauthorized) response when attempting to view other users' conversations.

    Returns:
        list[ConversationPublicWithMessages]: The conversations with their messages included.
    """
    if username is None: username = user.username
    if username != user.username and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to view these conversations")

    return session.exec(
        select(Conversation).order_by(desc(Conversation.created_at)).join(User).where(User.username == username).offset(offset).limit(limit)
    ).all()

@router.get("/conversations", response_model=list[ConversationPublic])
async def get_conversations_for_self(
    offset : int = 0, 
    limit : int = Query(default=100, le=100),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Obtain all conversations for the current user.

    Returns:
        list[ConversationPublicWithMessages]: The conversations with their messages included.
    """
    return session.exec(
        select(Conversation).order_by(desc(Conversation.created_at)).where(Conversation.user_id == user.id).offset(offset).limit(limit)
    ).all()

@router.delete("/conversation/{id}", response_model=Literal[True])
async def delete_conversation(
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Deletes a conversation for a given user.

    Args:
        id (int): The ID of the conversation to delete.

    Raises:
        HTTPException: Returns a 401 if the user tries to delete another user's conversation and is not an administrator.
    
    Returns:
        Literal[True]: Successful response.
    """
    conversation = session.get(Conversation, id)
    if not conversation: raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != user.id and not user.admin: raise HTTPException(status_code=401, detail="You are not authorised to delete this conversation")
    session.delete(conversation)
    session.commit()
    return True

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

async def add_llm_message_to_conversation(
    content : str,
    conversation_id : int,
    user : User,
    session : Session
) -> Conversation:
    """
    Adds a generated LLM response to an existing conversation.

    Args:
        content (str): The LLM response content.
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.

    Returns:
        Conversation: The conversation with the LLM response added to the list of messages.
    """

    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    assistant_message_data = MessageCreate(
        conversation_id = conversation_id,
        role="assistant",
        content=content
    )

    new_conversation = await add_message_to_conversation(
        assistant_message_data,
        user=user,
        session=session
    )

    return new_conversation

async def call_llm_response_to_conversation(
    conversation_id : int,
    user : User,
    magic : str,
    session : Session
) -> Conversation:
    """
    Queries the LLM to respond to a given conversation
    and adds its response to the list of messages.
    Assumes that the last message of the conversation was
    created by the user, not the LLM.

    Args:
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.
            Raises a 400 if the conversation does not have any messages (nothing to respond to).

    Returns:
        Conversation: The conversation with the LLM response added to the list of messages.
    """
    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    existing_messages = session.exec(
        select(Message).where(Message.conversation_id == existing_conversation.id)
    ).all()

    if not existing_messages:
        raise HTTPException(status_code=400, detail="A conversation must have messages to call an LLM response!")

    message_dict = [{
        "role": message.role, "content": message.content
    } for message in existing_messages]

    response_messages : list[BaseMessage] = await chat(
        user=user,
        magic=magic,
        session=session,
        messages=message_dict
    )

    response_text = response_messages[-1].content

    new_conversation = await add_llm_message_to_conversation(
        content=response_text,
        conversation_id = conversation_id,
        user=user,
        session=session
    )

    return new_conversation

async def stream_llm_response_to_conversation(
    conversation_id : int,
    background_tasks : BackgroundTasks,
    user : User,
    magic : str,
    session : Session
) -> AsyncGenerator[str, None]:
    """
    Queries the LLM to respond to a given conversation
    and adds its response to the list of messages.
    Uses LLM streaming to stream the response.

    Args:
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.
            Raises a 400 if the conversation does not have any messages (nothing to respond to).

    Returns:
        AsyncGenerator[str, None]: The LLM's response chunks.
    """
    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    existing_messages = session.exec(
        select(Message).where(Message.conversation_id == existing_conversation.id)
    ).all()

    if not existing_messages:
        raise HTTPException(status_code=400, detail="A conversation must have messages to call an LLM response!")

    message_dict = [{
        "role": message.role, "content": message.content
    } for message in existing_messages]

    # Call the function 'add_llm_message_to_conversation'
    # after the LLM stream has finished to add the response
    # to the database using a FastAPI background task.
    end_function = add_llm_message_to_conversation
    end_function_kwargs = {
        "user" : user,
        "session" : session,
        "conversation_id" : conversation_id,
    }

    return chat_stream(
        user=user,
        magic=magic,
        session=session,
        messages=message_dict,
        end_function=end_function,
        end_function_kwargs=end_function_kwargs,
        background_tasks=background_tasks
    )


@router.patch("/message/{message_id}", response_model=ConversationPublicWithMessages)
async def update_message_in_conversation(
    message_id : int,
    new_message_text : str,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Replace the content of a user message in a conversation
    with new text. DELETES all messages after the edited
    message and RETRIGGERS the LLM to respond to the
    edited message.

    Args:
        message_id (int): The ID of the message to replace.
        new_message_text (str): The new message text.
    
    Returns:
        ConversationPublicWithMessages:
            The conversation with the message updated.
    """
    existing_message = session.get(Message, message_id)
    if not existing_message: raise HTTPException(status_code=404, detail="Message not found")
    if not existing_message.role == "user": raise HTTPException(status_code=400, detail="You may not edit LLM messages")

    existing_conversation = session.get(Conversation, existing_message.conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")

    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to edit messages from another user's conversation")
    
    existing_message.sqlmodel_update({"content" : new_message_text})

    session.add(existing_message)
    session.commit()
    
    session.refresh(existing_conversation)

    if not existing_conversation.id: raise HTTPException(status_code=500, detail="Conversation ID missing")

    messages_to_delete = session.exec(
        select(Message).where(Message.conversation_id == existing_conversation.id).where(Message.id > existing_message.id)
    ).all()
    
    if messages_to_delete:
        for message in messages_to_delete:
            session.delete(message)

        session.commit()
        session.refresh(existing_conversation)
        
        existing_conversation = await call_llm_response_to_conversation(
            conversation_id = existing_conversation.id,
            user=user,
            magic=magic,
            session=session
        )

    return existing_conversation 

@router.delete("/message/{message_id}", response_model=ConversationPublicWithMessages)
async def delete_message_in_conversation(
    message_id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Delete a message from a conversation.

    Args:
        message_id (int): The ID of the message to delete.

    Returns:
        ConversationPublicWithMessages:
            The conversation with the message removed.
    """
    existing_message = session.get(Message, message_id)
    if not existing_message: raise HTTPException(status_code=404, detail="Message not found")
    existing_conversation = session.get(Conversation, existing_message.conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to remove messages from another user's conversation")
    session.delete(existing_message)
    session.commit()
    session.refresh(existing_conversation)
    return existing_conversation

@router.post("/conversation", response_model=ConversationPublicWithMessages)
async def conversation_start(
    new_message : NewMessage,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Create a new conversation with the LLM as the current user.
    Will return a new conversation object with a conversation ID,
    the user's message, and a response message from the LLM.

    Args:
        new_message (NewMessage): The user's message.

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
    
    conversation_with_response = await conversation_continue(
        conversation_id = conversation.id,
        new_message=new_message,
        user=user,
        magic=magic,
        session=session
    )

    return conversation_with_response

@router.post("/conversation_stream", response_class=StreamingResponse)
async def conversation_stream_start(
    new_message : NewMessage,
    background_tasks : BackgroundTasks,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Create a new conversation with the LLM as the current user.
    Will stream the LLM's response as chunks and add the LLM's
    response to the database when it is completed as a side
    effect using a FastAPI background task.

    Args:
        new_message (NewMessage): The user's message.

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

    return await conversation_stream_continue(
        conversation_id=conversation.id,
        new_message=new_message,
        background_tasks=background_tasks,
        user=user,
        magic=magic,
        session=session
    )

@router.post("/conversation/{conversation_id}", response_model=ConversationPublicWithMessages)
async def conversation_continue(
    conversation_id : int,
    new_message : NewMessage,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Continue an existing conversation with the LLM
    by sending a new message and awaiting a new
    LLM response.

    Args:
        conversation_id (int): The ID of the existing conversation.
        new_message (NewMessage): The user's message.

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
        content=new_message.message_text
    )
    
    new_conversation = await add_message_to_conversation(
        message_data,
        user=user,
        session=session
    )

    new_conversation = await call_llm_response_to_conversation(
        conversation_id=new_conversation.id,
        user=user,
        magic=magic,
        session=session
    )

    return new_conversation

@router.post("/conversation_stream/{conversation_id}", response_class=StreamingResponse)
async def conversation_stream_continue(
    conversation_id : int,
    new_message : NewMessage,
    background_tasks : BackgroundTasks,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Continue an existing conversation with the LLM
    by sending a new message and streaming the
    LLM's response as chunks. The LLM's response
    will be added to the conversation in the DB
    through a side effect once the generation is
    complete using a FastAPI background task.

    Args:
        conversation_id (int): The ID of the existing conversation.
        message_text (str): The content of the user's message.

    Returns:
        StreamingResponse: The LLM's response chunks.

    """
    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    message_data = MessageCreate(
        conversation_id = conversation_id,
        role="user",
        content=new_message.message_text
    )
    
    new_conversation = await add_message_to_conversation(
        message_data,
        user=user,
        session=session
    )

    return StreamingResponse(
        stream_llm_response_to_conversation(
            conversation_id=conversation_id,
            background_tasks=background_tasks,
            user=user,
            magic=magic,
            session=session
        ),
        media_type="text/plain"
    )