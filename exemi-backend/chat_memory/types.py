from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessageData:
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime


@dataclass
class ChatConversationData:
    id: int
    user_id: int
    created_at: datetime
    summary: str | None
    messages: list[ChatMessageData]


def openai_message_dict(message: ChatMessageData) -> dict[str, str]:
    return {"role": message.role, "content": message.content}
