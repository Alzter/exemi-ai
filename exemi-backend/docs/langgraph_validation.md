# LangGraph Hybrid Validation

Use this checklist after enabling `CHAT_MEMORY_BACKEND=langgraph_hybrid`.

## Functional checks

1. Start conversation:
   - `POST /conversation`
   - Expect assistant greeting + first user message persisted.
2. Reply generation:
   - `GET /conversation_reply/{id}`
   - Expect one assistant message appended.
3. Stream generation:
   - `GET /conversation_stream_reply/{id}`
   - Expect stream output and one final assistant message appended when stream ends.
4. Edit semantics:
   - `PATCH /message/{id}` on a user message
   - Expect all later messages in the same conversation to be removed.
5. Delete semantics:
   - `DELETE /message/{id}` removes one message.
   - `DELETE /conversation/{id}` removes conversation and dependent messages.

## Authorization checks

- Non-admin user cannot read another user's conversation.
- Non-admin user cannot mutate another user's messages.
- Admin user can fetch `POST /user_conversations`.

## Operational checks

- App boots when `LANGGRAPH_CHECKPOINTER=sqlite` and creates `LANGGRAPH_SQLITE_PATH`.
- App logs a warning and continues in SQL mode behavior if LangGraph deps are missing.
- No duplicate assistant rows after repeated stream retries.

## Rollback

Set:

```bash
CHAT_MEMORY_BACKEND=sql
```

This keeps transcript APIs unchanged while disabling LangGraph persistence usage for agent runs.
