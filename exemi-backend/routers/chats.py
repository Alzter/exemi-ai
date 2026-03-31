from pydantic import BaseModel, TypeAdapter
from ..models import Conversation, ConversationUpdate, ConversationPublic, ConversationPublicWithMessages
from ..models import User, NewMessage, Message, MessageCreate
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, desc
from ..dependencies import get_current_magic, get_current_user, get_session
from ..date_utils import parse_timestamp
from ..llm_api import chat, chat_stream, summarise
from langchain_core.messages import BaseMessage
from datetime import datetime, timezone
from typing import Literal
import json

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

    conversation = session.get(Conversation, id)

    if not conversation: raise HTTPException(status_code=404, detail=f"Conversation not found with ID {id}")

    if not conversation.user_id == user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to view this conversation")

    return conversation

@router.post("/user_conversations", response_model=list[ConversationPublicWithMessages])
async def get_user_conversations(
    date : datetime = datetime(day=27,month=2,year=2026),
    limit : int = Query(default=100, le=500),
    current_user : User = Depends(get_current_user),
    session : Session = Depends(get_session),
):
    if not current_user.admin: raise HTTPException(status_code=401,detail="Unauthorised")

    messages = session.exec(
        select(Conversation)
        .join(User)
        .where(Conversation.created_at >= date)
        .where(User.admin == False)
        .order_by(Conversation.created_at)
        .limit(limit)
    ).all()
    
    return messages

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

@router.patch("/conversation/{id}", response_model=ConversationPublicWithMessages)
async def update_conversation(
    data : ConversationUpdate,
    id : int,
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Assign a conversation summary to a given
    conversation.

    Args:
        data (ConversationUpdate): The conversation summary to add.
        id (int): The ID of the conversation to update.
    
    Raises:
        HTTPException:
            If the current user is not an administrator, this will return a 401 (Unauthorized) response when attempting to update other users' conversations.
            This will also return a 404 (not found) if the conversation did not exist in the DB.

    Returns:
        ConversationPublicWithMessages: The conversation with the summary added.
    """

    existing_conversation : Conversation = await get_conversation(
        id = id,
        user = user,
        session = session
    )

    update = data.model_dump(exclude_unset=False)

    existing_conversation.sqlmodel_update(update)

    session.add(existing_conversation)
    session.commit()
    session.refresh(existing_conversation)
    
    return existing_conversation

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

async def add_messages_to_conversation(
    messages : list[dict[str,str]],
    conversation_id : int,
    user : User,
    session : Session
) -> Conversation:
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

    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    for message in messages:

        if not message.get("role") or not message.get("content"):
            raise HTTPException(status_code=400, detail="Chat messages must contain a 'role' and 'content' field!")
        
        message_data = MessageCreate(
            conversation_id = conversation_id,
            role=message.get("role"),
            content=message.get("content")
        )

        new_conversation = await add_message_to_conversation(
            message_data,
            user=user,
            session=session
        )

    return new_conversation

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

    conversation_data = {
        "user_id" : user.id,
        "unit_id" : new_message.unit_id,
        "user" : user,
        "created_at" : datetime.now(timezone.utc)
    }

    conversation = Conversation.model_validate(conversation_data)

    # Get the conversation's greeting message
    # *before* we add it to the database, since
    # the get_conversation_greeting method checks
    # if we have any existing conversations in the
    # DB to determine whether to show the initial
    # greeting message or not.

    # existing_conversations : list[Conversation] = await get_conversations_for_self(offset=0, limit=1, user=user, session=session)
    
    # is_first_conversation = len(existing_conversations) == 0
    
    greeting_message = await get_conversation_greeting(
        user=user, session=session
    )

    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    if not conversation:
        raise HTTPException(status_code=500, detail="System error creating conversation!")
    
    # Add the chatbot's initial "greeting"
    # message to the conversation.

    # if is_first_conversation:
    greeting_message_data = MessageCreate(
        conversation_id=conversation.id,
        role="assistant",
        content = greeting_message
    )

    await add_message_to_conversation(
        greeting_message_data,
        user=user,
        session=session
    )

    conversation_with_response = await conversation_continue(
        conversation_id = conversation.id,
        new_message=new_message,
        user=user,
        session=session
    )

    return conversation_with_response

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

    return new_conversation


def get_message_list_from_conversation_object(
    conversation : Conversation
) -> list[dict[str, str]]:
    """
    Obtains a list of mesasges from an
    existing conversation in the OpenAI
    chat message template format.

    Args:
        conversation (Conversation): The conversation to obtain the message list for.

    Returns:
        list[dict[str, str]]: The messages with "role" and "content" fields.
    """

    conversation = ConversationPublicWithMessages.model_validate(conversation)
    messages = conversation.messages

    message_dict = [{
        "role": message.role, "content": message.content
    } for message in messages]

    return message_dict

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
    existing_conversation = session.get(Conversation, conversation_id)
    if not existing_conversation: raise HTTPException(status_code=404, detail="Conversation not found")
    
    if existing_conversation.user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail="You are not authorised to add messages to another user's conversation")

    return get_message_list_from_conversation_object(
        conversation=existing_conversation
    )


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
        messages=messages
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

    conversation : Conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=500, detail="Error responding to conversation: Could not obtain conversation object!")

    messages = get_message_list(conversation_id=conversation_id, user=user, session=session)
    if not messages:
        raise HTTPException(status_code=500, detail="Error responding to conversation: Conversation is empty!")
    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=500, detail="Error responding to conversation: Last message must be created by the user!")
    

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
            unit_id=conversation.unit_id,
            background_tasks=background_tasks,
            end_function=end_function,
            end_function_kwargs=end_function_kwargs
        ),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no"
        }
    )

    return response

async def create_conversation_summary(
    conversation : Conversation,
    user : User,
    session : Session,
    max_words : int = 50
) -> Conversation:
    """
    Generate a summary for a given conversation,
    or obtain it from the database if it has already
    been created.

    Args:
        conversation (Conversation): The conversation object to summarise.
        user (User): The currently logged-in user.
        session (Session): SQLModel connection with the database.
        max_words (int, optional): Conversation summary word limit. Defaults to 50.

    Returns:
        Conversation:
            The conversation with the summary added.
    """

    # Return the conversation summary if it exists
    if conversation.summary:
        return conversation

    # Create a summary if not exists
    
    # Obtain OpenAI-formatted list of messages for the conversation
    messages : list[dict[str,str]] = get_message_list_from_conversation_object(
        conversation=conversation
    )

    # Get LLM to summarise conversation text
    summary : str = await summarise(
        chat_message_log = messages,
        max_words = max_words
    )
    
    conversation_pub = ConversationPublic.model_validate(conversation)

    conversation = await update_conversation(
        data = ConversationUpdate(summary = summary),
        id = conversation_pub.id,
        user = user,
        session = session
    )

    return conversation

@router.get("/conversation_summary/{id}", response_model=ConversationPublic)
async def get_conversation_summary(
    id : int,
    max_words : int = Query(default=50, le=500),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
):
    """
    Generate a summary for a given conversation,
    or obtain it from the database if it has already
    been created.

    Args:
        id (int): ID of the conversation to summarise.
        max_words (int, optional): Conversation summary word limit. Defaults to 50. Max of 500.

    Raises:
        HTTPException:
            Raises a 401 if the conversation was not created by the current user and the user is not an admin.
            Raises a 404 if the conversation does not exist.

    Returns:
        ConversationPublic:
            The conversation with a summary added.
    """
    conversation = await get_conversation(
        id = id,
        user = user,
        session = session
    )

    summary = await create_conversation_summary(
        conversation = conversation,
        user = user,
        session = session,
        max_words = max_words
    )

    return summary

class ConversationSummary(BaseModel):
    summary : str
    date : datetime

@router.get("/tool/conversation_summaries", response_model=list[ConversationSummary])
async def get_conversation_summaries(
    offset : int = 1,
    limit : int = Query(default=5, le=10),
    creation_limit : int = Query(default=1, le=5),
    max_words : int = Query(default=50, le=500),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> list[ConversationSummary]:
    """
    Get the first *n* (``limit``) of the user's most recent conversations,
    and create summaries for the first *m* (``creation_limit``)
    of these *n* conversations. Return all *n* conversations in a list.

    Args:
        offset (int, optional):
            Skip the first *n* most recent conversations. Defaults to 1.
        limit (int, optional):
            Maximum number of summaries to retrieve. Defaults to 5. Max of 10.
        creation_limit (int, optional):
            Maximum number of new conversation summaries to create. Defaults to 1. Max of 5.
        max_words (int, optional): Conversation summary word limit. Defaults to 50. Max of 500.

    Returns:
        list[ConversationSummary]: A list of conversation summaries.
    """

    conversations = await get_conversations_for_self(
        offset=offset,
        limit=limit,
        user=user,
        session=session
    )

    conversations = list(conversations)

    for i in range(creation_limit):
        conversations[i] = await create_conversation_summary(
            conversation=conversations[i],
            max_words=max_words,
            user=user,
            session=session
        )
    
    # Filter out all conversations which don't have a summmary
    conversations = [c for c in conversations if c.summary]

    summaries = [
        ConversationSummary(
            date = conversation.created_at,
            summary = conversation.summary or ""
        ) for conversation in conversations
    ]

    return summaries

summary_list_adapter = TypeAdapter(list[ConversationSummary])

@router.get("/tool/conversation_summaries_json", response_model=str)
async def get_conversation_summaries_json(
    offset : int = 1,
    limit : int = Query(default=5, le=10),
    creation_limit : int = Query(default=1, le=5),
    max_words : int = Query(default=50, le=500),
    user : User = Depends(get_current_user),
    session : Session = Depends(get_session)
) -> str:
    """
    Obtain a string representing a JSON object of a list
    of conversation summaries with timestamps attached.

    See ``get_conversation_summaries()`` for more
    information on how the conversation summaries
    are created / cached.

    Args:
        offset (int, optional):
            Skip the first *n* most recent conversations. Defaults to 1.
        limit (int, optional):
            Maximum number of summaries to retrieve. Defaults to 5. Max of 10.
        creation_limit (int, optional):
            Maximum number of new conversation summaries to create. Defaults to 1. Max of 5.
        max_words (int, optional): Conversation summary word limit. Defaults to 50. Max of 500.

    Returns:
        str: The conversation summary data.
    """

    summaries : list[ConversationSummary] = await get_conversation_summaries(
        offset=offset,
        limit=limit,
        creation_limit=creation_limit,
        max_words=max_words,
        user=user,
        session=session
    )

    return summary_list_adapter.dump_json(summaries).decode("utf-8")

    # summaries = [{
    #     "date" : str(parse_timestamp(conversation.created_at)),
    #     "summary" : conversation.summary
    # } for conversation in conversations]

    # return json.dumps(summaries, ensure_ascii=False).encode("utf-8")
