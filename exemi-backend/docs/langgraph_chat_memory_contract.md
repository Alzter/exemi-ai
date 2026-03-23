# Chat Memory Contract (Legacy SQL vs LangGraph Hybrid)

This document captures the chat endpoint behaviors that must remain stable while migrating memory to LangGraph.

## Endpoint Contract Mapping

| Endpoint | Existing behavior | LangGraph hybrid behavior |
| --- | --- | --- |
| `GET /conversation/{id}` | Returns conversation metadata + ordered messages for owner/admin. | Same response shape. Data served through `ChatMemoryService`; SQL transcript remains API-compatible view. |
| `GET /conversations` | Returns current user's conversations newest-first (paged). | Same behavior. |
| `GET /conversations/{username}` | Admin can read other users, normal users only self. | Same behavior. |
| `POST /conversation` | Creates conversation, appends greeting assistant message then first user message. | Same behavior + deterministic LangGraph `thread_id` (`conversation:<id>`) for agent memory. |
| `POST /conversation/{conversation_id}` | Appends new user message to existing conversation. | Same behavior. |
| `GET /conversation_reply/{conversation_id}` | Invokes LLM and persists assistant response in background task. | Same behavior + LLM invocation includes LangGraph `thread_id` when enabled. |
| `GET /conversation_stream_reply/{conversation_id}` | Streams response and persists assistant content after stream completes. | Same behavior + stream invocation includes LangGraph `thread_id` when enabled. |
| `PATCH /message/{message_id}` | User messages only; edit selected message and delete subsequent tail. | Same behavior preserved in compatibility layer. |
| `DELETE /message/{message_id}` | Delete a single message if owner/admin. | Same behavior preserved in compatibility layer. |
| `DELETE /conversation/{id}` | Delete conversation and cascade messages. | Same behavior preserved in compatibility layer. |

## Ownership/Auth Guarantees

- Conversation reads and writes require `conversation.user_id == current_user.id` unless admin.
- Username-scoped listing for another user remains admin-only.
- Message-level updates/deletes still inherit conversation ownership checks.

## Why Hybrid During Migration

- Frontend/API currently depends on integer `message.id` for edit/delete operations.
- LangGraph checkpoints are state snapshots and do not natively expose mutable row-level message IDs.
- Hybrid mode lets LangGraph become the conversation runtime memory layer without breaking current REST contracts.
