import os
import warnings
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus


_checkpointer: Any = None
_store: Any = None
_initialised = False
_checkpointer_cm: AbstractContextManager | None = None


def using_langgraph_memory() -> bool:
    backend = os.getenv("CHAT_MEMORY_BACKEND", "sql").strip().lower()
    return backend in {"langgraph", "langgraph_hybrid"}


def _build_postgres_uri(prefix: str = "LANGGRAPH_POSTGRES") -> str | None:
    """
    Build a PostgreSQL URI from split env vars.
    Falls back to <prefix>_URI for backward compatibility.
    """
    explicit_uri = os.getenv(f"{prefix}_URI")
    if explicit_uri:
        return explicit_uri

    user = os.getenv(f"{prefix}_USER")
    password = os.getenv(f"{prefix}_PASS")
    host = os.getenv(f"{prefix}_HOST")
    port = os.getenv(f"{prefix}_PORT", "5432")
    database = os.getenv(f"{prefix}_DB")

    if not all([user, password, host, database]):
        return None

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )


def _build_checkpointer():
    backend = os.getenv("LANGGRAPH_CHECKPOINTER", "sqlite").strip().lower()
    if backend == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver

        postgres_uri = _build_postgres_uri("LANGGRAPH_POSTGRES")
        if not postgres_uri:
            raise RuntimeError(
                "Set LANGGRAPH_POSTGRES_URI or LANGGRAPH_POSTGRES_USER/PASS/HOST/PORT/DB "
                "when LANGGRAPH_CHECKPOINTER=postgres"
            )
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

        postgres_uri = _build_postgres_uri("LANGGRAPH_STORE_POSTGRES") or _build_postgres_uri("LANGGRAPH_POSTGRES")
        if not postgres_uri:
            raise RuntimeError(
                "Set LANGGRAPH_STORE_POSTGRES_URI or LANGGRAPH_STORE_POSTGRES_USER/PASS/HOST/PORT/DB "
                "(or LANGGRAPH_POSTGRES_*) when LANGGRAPH_STORE=postgres"
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
