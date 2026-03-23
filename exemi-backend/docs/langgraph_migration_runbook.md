# LangGraph Migration Runbook

## Objective

Move conversation memory runtime to LangGraph while preserving existing API contracts.

## Configuration

Set these environment variables in `exemi-backend/.env`:

```bash
CHAT_MEMORY_BACKEND=langgraph_hybrid
LANGGRAPH_CHECKPOINTER=sqlite
LANGGRAPH_SQLITE_PATH=.data/langgraph_checkpoints.sqlite
LANGGRAPH_STORE=memory
```

Production-oriented PostgreSQL setup:

```bash
CHAT_MEMORY_BACKEND=langgraph_hybrid
LANGGRAPH_CHECKPOINTER=postgres
LANGGRAPH_POSTGRES_USER=postgres
LANGGRAPH_POSTGRES_PASS=YOURSTRONGPASSWORD
LANGGRAPH_POSTGRES_HOST=127.0.0.1
LANGGRAPH_POSTGRES_PORT=5432
LANGGRAPH_POSTGRES_DB=exemi_langgraph
LANGGRAPH_STORE=postgres
LANGGRAPH_STORE_POSTGRES_USER=postgres
LANGGRAPH_STORE_POSTGRES_PASS=YOURSTRONGPASSWORD
LANGGRAPH_STORE_POSTGRES_HOST=127.0.0.1
LANGGRAPH_STORE_POSTGRES_PORT=5432
LANGGRAPH_STORE_POSTGRES_DB=exemi_langgraph
```

## Phased Rollout

1. Deploy with `CHAT_MEMORY_BACKEND=sql` (no behavior change).
2. Enable `langgraph_hybrid` in staging and verify:
   - `GET /conversation_reply/{id}` writes expected transcript.
   - `GET /conversation_stream_reply/{id}` writes one final assistant message.
   - Message edit/delete endpoints still work.
3. Backfill existing conversations into LangGraph threads (optional but recommended).
4. Enable hybrid in production.
5. Monitor for duplicate assistant messages and auth regressions.

## Backfill

Use `scripts/backfill_langgraph_threads.py` to replay existing conversations into LangGraph threads.

Example:

```bash
cd exemi-backend
python scripts/backfill_langgraph_threads.py --limit 200 --dry-run
python scripts/backfill_langgraph_threads.py --limit 200
```

Notes:
- The script replays user turns into thread IDs in the format `conversation:<id>`.
- It is idempotent at the conversation level when your replay policy only targets conversations not yet replayed (recommend running in batches and tracking job output externally).

## Validation Checklist

- Auth:
  - normal user cannot access another user's conversation
  - admin can query `POST /user_conversations`
- Streaming:
  - aborted stream does not append empty assistant messages
  - completed stream appends exactly one assistant final message
- Edit semantics:
  - `PATCH /message/{id}` truncates tail messages
- Hybrid memory:
  - repeated calls on same conversation include `thread_id=conversation:<id>` and preserve context
