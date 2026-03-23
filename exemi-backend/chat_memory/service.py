import os
from datetime import datetime, timezone
from sqlmodel import Session, select, desc
from fastapi import HTTPException

from ..models import Conversation, Message, MessageCreate, User
from .types import ChatConversationData, ChatMessageData, openai_message_dict


def _to_message_data(message: Message) -> ChatMessageData:
    if message.id is None:
        raise HTTPException(status_code=500, detail="Message ID missing")
    return ChatMessageData(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _to_conversation_data(conversation: Conversation, messages: list[Message]) -> ChatConversationData:
    if conversation.id is None:
        raise HTTPException(status_code=500, detail="Conversation ID missing")
    return ChatConversationData(
        id=conversation.id,
        user_id=conversation.user_id,
        created_at=conversation.created_at,
        summary=conversation.summary,
        messages=[_to_message_data(message) for message in messages],
    )


def _assert_owner_or_admin(user: User, owner_user_id: int, unauthorised_detail: str):
    if owner_user_id != user.id and not user.admin:
        raise HTTPException(status_code=401, detail=unauthorised_detail)


class ChatMemoryService:
    """
    Compatibility layer that decouples router logic from direct SQLModel access.
    The default implementation remains SQL-backed and can be extended with
    LangGraph synchronization via thread IDs.
    """

    def __init__(self):
        self.backend = os.getenv("CHAT_MEMORY_BACKEND", "sql").strip().lower()

    def get_thread_id(self, conversation_id: int) -> str:
        return f"conversation:{conversation_id}"

    def get_conversation(self, conversation_id: int, user: User, session: Session) -> ChatConversationData:
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation not found with ID {conversation_id}")
        _assert_owner_or_admin(user, conversation.user_id, "You are not authorised to view this conversation")
        messages = session.exec(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).all()
        return _to_conversation_data(conversation, messages)

    def get_user_conversations_since(
        self, date: datetime, limit: int, current_user: User, session: Session
    ) -> list[ChatConversationData]:
        if not current_user.admin:
            raise HTTPException(status_code=401, detail="Unauthorised")
        conversations = session.exec(
            select(Conversation)
            .join(User)
            .where(Conversation.created_at >= date)
            .where(User.admin == False)  # noqa: E712
            .order_by(Conversation.created_at)
            .limit(limit)
        ).all()
        return [self.get_conversation(conversation.id, current_user, session) for conversation in conversations if conversation.id is not None]

    def get_conversations_for_user(
        self, username: str | None, offset: int, limit: int, user: User, session: Session
    ) -> list[Conversation]:
        if username is None:
            username = user.username
        if username != user.username and not user.admin:
            raise HTTPException(status_code=401, detail="You are not authorised to view these conversations")
        return session.exec(
            select(Conversation)
            .order_by(desc(Conversation.created_at))
            .join(User)
            .where(User.username == username)
            .offset(offset)
            .limit(limit)
        ).all()

    def get_conversations_for_self(
        self, offset: int, limit: int, user: User, session: Session
    ) -> list[Conversation]:
        return session.exec(
            select(Conversation)
            .order_by(desc(Conversation.created_at))
            .where(Conversation.user_id == user.id)
            .offset(offset)
            .limit(limit)
        ).all()

    def delete_conversation(self, conversation_id: int, user: User, session: Session) -> bool:
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        _assert_owner_or_admin(user, conversation.user_id, "You are not authorised to delete this conversation")
        session.delete(conversation)
        session.commit()
        return True

    def add_message(self, data: MessageCreate, user: User, session: Session) -> ChatConversationData:
        existing_conversation = session.get(Conversation, data.conversation_id)
        if not existing_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        _assert_owner_or_admin(
            user,
            existing_conversation.user_id,
            "You are not authorised to add messages to another user's conversation",
        )
        message = Message.model_validate(data, update={"created_at": datetime.now(timezone.utc)})
        session.add(message)
        session.commit()
        return self.get_conversation(data.conversation_id, user, session)

    def add_messages(
        self, messages: list[dict[str, str]], conversation_id: int, user: User, session: Session
    ) -> ChatConversationData:
        existing_conversation = session.get(Conversation, conversation_id)
        if not existing_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        _assert_owner_or_admin(
            user,
            existing_conversation.user_id,
            "You are not authorised to add messages to another user's conversation",
        )
        for message in messages:
            if not message.get("role") or not message.get("content"):
                raise HTTPException(
                    status_code=400,
                    detail="Chat messages must contain a 'role' and 'content' field!",
                )
            self.add_message(
                MessageCreate(
                    conversation_id=conversation_id,
                    role=message["role"],
                    content=message["content"],
                ),
                user=user,
                session=session,
            )
        return self.get_conversation(conversation_id, user, session)

    def create_conversation(
        self, user: User, greeting_message: str, first_user_message: str, session: Session
    ) -> ChatConversationData:
        conversation = Conversation.model_validate(
            {"user_id": user.id, "user": user, "created_at": datetime.now(timezone.utc)}
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        if conversation.id is None:
            raise HTTPException(status_code=500, detail="System error creating conversation!")

        self.add_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="assistant",
                content=greeting_message,
            ),
            user=user,
            session=session,
        )
        self.add_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="user",
                content=first_user_message,
            ),
            user=user,
            session=session,
        )
        return self.get_conversation(conversation.id, user, session)

    def append_user_message(
        self, conversation_id: int, message_text: str, user: User, session: Session
    ) -> ChatConversationData:
        return self.add_message(
            MessageCreate(conversation_id=conversation_id, role="user", content=message_text),
            user=user,
            session=session,
        )

    def get_openai_messages(self, conversation_id: int, user: User, session: Session) -> list[dict[str, str]]:
        conversation_data = self.get_conversation(conversation_id, user, session)
        return [openai_message_dict(message) for message in conversation_data.messages]

    def update_user_message_and_truncate(
        self, message_id: int, new_message_text: str, user: User, session: Session
    ) -> ChatConversationData:
        existing_message = session.get(Message, message_id)
        if not existing_message:
            raise HTTPException(status_code=404, detail="Message not found")
        if existing_message.role != "user":
            raise HTTPException(status_code=400, detail="You may not edit LLM messages")
        conversation = session.get(Conversation, existing_message.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        _assert_owner_or_admin(
            user,
            conversation.user_id,
            "You are not authorised to edit messages from another user's conversation",
        )
        existing_message.sqlmodel_update({"content": new_message_text})
        session.add(existing_message)
        session.commit()
        messages_to_delete = session.exec(
            select(Message)
            .where(Message.conversation_id == existing_message.conversation_id)
            .where(Message.id > message_id)
        ).all()
        for message in messages_to_delete:
            session.delete(message)
        if messages_to_delete:
            session.commit()
        return self.get_conversation(existing_message.conversation_id, user, session)

    def delete_message(self, message_id: int, user: User, session: Session) -> ChatConversationData:
        existing_message = session.get(Message, message_id)
        if not existing_message:
            raise HTTPException(status_code=404, detail="Message not found")
        existing_conversation = session.get(Conversation, existing_message.conversation_id)
        if not existing_conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        _assert_owner_or_admin(
            user,
            existing_conversation.user_id,
            "You are not authorised to remove messages from another user's conversation",
        )
        session.delete(existing_message)
        session.commit()
        return self.get_conversation(existing_conversation.id, user, session)
