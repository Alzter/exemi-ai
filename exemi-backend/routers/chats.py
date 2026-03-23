from ..models import User, Conversation, NewMessage, ConversationPublic, ConversationPublicWithMessages, Message, MessageCreate
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, desc
from ..dependencies import get_current_magic, get_current_user, get_session
from ..llm_api import chat, chat_stream
from langchain_core.messages import BaseMessage
from datetime import datetime, timezone
from typing import Literal
from ..chat_memory import ChatMemoryService
from ..chat_memory.types import ChatConversationData

router = APIRouter()
memory_service = ChatMemoryService()


def _conversation_data_to_response(conversation: ChatConversationData) -> dict:
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at,
        "messages": [
            {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in conversation.messages
        ],
    }

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
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no"
        }
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

    conversation = memory_service.get_conversation(conversation_id=id, user=user, session=session)
    return _conversation_data_to_response(conversation)

@router.post("/user_conversations", response_model=list[ConversationPublicWithMessages])
async def get_user_conversations(
    date : datetime = datetime(day=27,month=2,year=2026),
    limit : int = Query(default=100, le=500),
    current_user : User = Depends(get_current_user),
    session : Session = Depends(get_session),
):
    conversations = memory_service.get_user_conversations_since(
        date=date, limit=limit, current_user=current_user, session=session
    )
    return [_conversation_data_to_response(conversation) for conversation in conversations]

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
    return memory_service.get_conversations_for_user(
        username=username, offset=offset, limit=limit, user=user, session=session
    )

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
    return memory_service.get_conversations_for_self(offset=offset, limit=limit, user=user, session=session)

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
    return memory_service.delete_conversation(conversation_id=id, user=user, session=session)

# @router.post("/message", response_model=ConversationPublicWithMessages)
async def add_message_to_conversation(
    data : MessageCreate,
    user : User,
    session : Session
):
    conversation = memory_service.add_message(data=data, user=user, session=session)
    return _conversation_data_to_response(conversation)

async def add_messages_to_conversation(
    messages : list[dict[str,str]],
    conversation_id : int,
    user : User,
    session : Session
) -> dict:
    """
    Add a list of messages in the OpenAI chat template
    format to an existing conversation.

    Args:
        messages (list[dict[str,str]]): The messages in OpenAI chat template format.
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.

    Returns:
        Conversation: The conversation with the LLM response added to the list of messages.
    """

    conversation = memory_service.add_messages(
        messages=messages, conversation_id=conversation_id, user=user, session=session
    )
    return _conversation_data_to_response(conversation)

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
    message.

    Args:
        message_id (int): The ID of the message to replace.
        new_message_text (str): The new message text.
    
    Returns:
        ConversationPublicWithMessages:
            The conversation with the message updated.
    """
    conversation = memory_service.update_user_message_and_truncate(
        message_id=message_id,
        new_message_text=new_message_text,
        user=user,
        session=session,
    )
    return _conversation_data_to_response(conversation)

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
    conversation = memory_service.delete_message(message_id=message_id, user=user, session=session)
    return _conversation_data_to_response(conversation)

@router.get("/conversation_greeting", response_model=str)
async def get_conversation_greeting(
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Unlike general-purpose chatbots, the Exemi chatbot initiates conversations
    with the user by sending an assistant message *first*. This function
    obtains the contents of the first assistant message to send the user
    to begin a conversation with them.
    
    Returns:
        str: The greeting message.
    """

    existing_conversations = await get_conversations_for_self(offset=0, limit=1, user=user, session=session)
    
    is_first_conversation = len(existing_conversations) == 0

    if is_first_conversation:
        return """
Hi, I'm **Exemi**! I'm an AI chatbot designed to
help you plan and manage your time for your university course 😊

I can help you with:
- identifying upcoming assignment deadlines,
- breaking assignments down into smaller tasks,
- setting reminders for assignment tasks, and
- using practical strategies to reduce stress.

I am an **early prototype** of what could become a fully-featured AI
study assistant for students like you! Since I'm still in development,
**you may find issues or bugs** when using me. If this happens to you,
please let the researchers know in the feedback survey 👍
        """.strip()
    
    else:
        return f"## Hello! How can I help you today?"

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
    the LLM's initial message (see get_conversation_greeting) and
    the user's message.

    Args:
        new_message (NewMessage): The user's message text.

    Returns:
        ConversationPublicWithMessages: The new conversation.
    """

    greeting_message = await get_conversation_greeting(
        user=user, session=session
    )
    conversation = memory_service.create_conversation(
        user=user,
        greeting_message=greeting_message,
        first_user_message=new_message.message_text,
        session=session,
    )
    return _conversation_data_to_response(conversation)

@router.post("/conversation/{conversation_id}", response_model=ConversationPublicWithMessages)
async def conversation_continue(
    conversation_id : int,
    new_message : NewMessage,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Continue an existing conversation with the LLM
    by sending a new message.

    Args:
        conversation_id (int): The ID of the existing conversation.
        new_message (NewMessage): The user's message text.

    Returns:
        ConversationPublicWithMessages:
            The conversation updated to include the new user message.
    """
    conversation = memory_service.append_user_message(
        conversation_id=conversation_id,
        message_text=new_message.message_text,
        user=user,
        session=session,
    )
    return _conversation_data_to_response(conversation)

def get_message_list(
    conversation_id : int,
    user : User,
    session : Session
) -> list[dict[str, str]]:
    """
    Obtains a list of mesasges from an
    existing conversation in the OpenAI
    chat message template format.

    Args:
        conversation_id (int): Conversation ID to retrieve.

    Returns:
        list[dict[str, str]]: The messages with "role" and "content" fields.
    """
    return memory_service.get_openai_messages(conversation_id=conversation_id, user=user, session=session)


@router.get("/conversation_reply/{conversation_id}", response_model=str)
async def call_llm_response_to_conversation(
    conversation_id : int,
    background_tasks : BackgroundTasks,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Queries the LLM to respond to a given conversation.
    Returns the LLM's response text. Adds the LLM's response
    to the list of messages in the conversation as a side
    effect using a background task.

    Args:
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.
            Raises a 400 if the conversation does not have any messages (nothing to respond to).
            Raises a 400 if the last message in the conversation was not a user message.

    Returns:
        str: The LLM's response text.
    """
    messages = get_message_list(conversation_id=conversation_id, user=user, session=session)
    if not messages:
        raise HTTPException(status_code=400, detail="Error responding to conversation: conversation is empty!")
    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Error responding to conversation: last message must be created by the user!")

    response_messages : list[BaseMessage] = await chat(
        user=user,
        magic=magic,
        session=session,
        messages=messages,
        thread_id=memory_service.get_thread_id(conversation_id),
    )

    response_text = str(response_messages[-1].content)

    response_messages = [{"role":"assistant","content":response_text}]
    
    background_tasks.add_task(
        add_messages_to_conversation,
        messages=response_messages,
        conversation_id = conversation_id,
        user=user,
        session=session
    )

    return response_text

@router.get("/conversation_stream_reply/{conversation_id}", response_class=StreamingResponse)
async def stream_llm_response_to_conversation(
    conversation_id : int,
    background_tasks : BackgroundTasks,
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic),
    session : Session = Depends(get_session)
):
    """
    Queries the LLM to respond to a given conversation.
    Returns the LLM's response text. Adds the LLM's response
    to the list of messages in the conversation as a side
    effect using a background task.

    Args:
        conversation_id (int): The conversation ID.

    Raises:
        HTTPException:
            Raises a 404 if the conversation does not exist.
            Raises a 401 if the user attempts to call the LLM to respond to another user's conversation.
            Raises a 400 if the conversation does not have any messages (nothing to respond to).
            Raises a 400 if the last message in the conversation was not a user message.

    Returns:
        StreamingResponse: The LLM's response text in chunks.
    """
    messages = get_message_list(conversation_id=conversation_id, user=user, session=session)
    if not messages:
        raise HTTPException(status_code=400, detail="Error responding to conversation: conversation is empty!")
    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="Error responding to conversation: last message must be created by the user!")
    

    # Declare a function to add the LLM's response to
    # the database. Call this function using a background
    # task after the LLM has finished streaming the response.
    end_function = add_messages_to_conversation
    end_function_kwargs = {
        "conversation_id" : conversation_id,
        "user" : user,
        "session" : session
    }
    
    response = StreamingResponse(
        chat_stream(
            user=user,
            magic=magic,
            session=session,
            messages=messages,
            background_tasks=background_tasks,
            end_function=end_function,
            end_function_kwargs=end_function_kwargs,
            thread_id=memory_service.get_thread_id(conversation_id),
        ),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no"
        }
    )

    return response
