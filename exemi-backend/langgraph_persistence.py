import os
import warnings
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any


_checkpointer: Any = None
_store: Any = None
_initialised = False
_checkpointer_cm: AbstractContextManager | None = None


def using_langgraph_memory() -> bool:
    backend = os.getenv("CHAT_MEMORY_BACKEND", "sql").strip().lower()
    return backend in {"langgraph", "langgraph_hybrid"}


def _build_checkpointer():
    backend = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite").strip().lower()
    if backend == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver

        postgres_uri = os.getenv("LANGGRAPH_POSTGRES_URI")
        if not postgres_uri:
            raise RuntimeError("LANGGRAPH_POSTGRES_URI is required when LANGGRAPH_CHECKPOINTER=postgres")
        context_manager = PostgresSaver.from_conn_string(postgres_uri)
        saver = context_manager.__enter__()
        saver.setup()
        return saver, context_manager

    if backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        sqlite_path = os.getenv("LANGGRAPH_SQLITE_PATH", ".data/langgraph_checkpoints.sqlite")
        sqlite_file = Path(sqlite_path)
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver.from_conn_string(str(sqlite_file)), None

    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver(), None


def _build_store():
    backend = os.getenv("LANGGRAPH_STORE", "memory").strip().lower()
    if backend == "postgres":
        from langgraph.store.postgres import PostgresStore

        postgres_uri = os.getenv("LANGGRAPH_STORE_POSTGRES_URI") or os.getenv("LANGGRAPH_POSTGRES_URI")
        if not postgres_uri:
            raise RuntimeError(
                "LANGGRAPH_STORE_POSTGRES_URI or LANGGRAPH_POSTGRES_URI is required when LANGGRAPH_STORE=postgres"
            )
        context_manager = PostgresStore.from_conn_string(postgres_uri)
        store = context_manager.__enter__()
        store.setup()
        return store

    if backend == "redis":
        from langgraph.store.redis import RedisStore

        redis_uri = os.getenv("LANGGRAPH_REDIS_URI", "redis://localhost:6379")
        return RedisStore.from_conn_string(redis_uri)

    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def get_langgraph_resources() -> tuple[Any | None, Any | None]:
    global _checkpointer, _store, _initialised, _checkpointer_cm

    if not using_langgraph_memory():
        return None, None
    if _initialised:
        return _checkpointer, _store

    try:
        _checkpointer, _checkpointer_cm = _build_checkpointer()
        _store = _build_store()
        _initialised = True
    except Exception as exc:
        warnings.warn(f"LangGraph persistence disabled: {exc}")
        _checkpointer = None
        _store = None
        _initialised = True
    return _checkpointer, _store


def close_langgraph_resources():
    global _checkpointer_cm
    if _checkpointer_cm is not None:
        _checkpointer_cm.__exit__(None, None, None)
        _checkpointer_cm = None
