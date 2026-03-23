#!/usr/bin/env python3
"""Export SQL conversation transcripts for LangGraph replay jobs."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.engine import URL  # noqa: E402
from sqlmodel import Session, create_engine, select  # noqa: E402
from models import Conversation, Message  # type: ignore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export SQL transcripts into replay payloads for LangGraph.")
    parser.add_argument("--offset", type=int, default=0, help="Conversation offset")
    parser.add_argument("--limit", type=int, default=200, help="Max conversations to process")
    parser.add_argument(
        "--output",
        default="langgraph_backfill_payloads.jsonl",
        help="Output JSONL file path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print summary")
    return parser.parse_args()


def get_engine():
    db_driver = os.getenv("DB_DRIVER", "mariadb+mariadbconnector")
    url = URL.create(
        db_driver,
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
    )
    return create_engine(url, echo=False)


def main():
    args = parse_args()
    engine = get_engine()
    written = 0
    output_file = Path(args.output)

    with Session(engine) as session:
        conversations = session.exec(
            select(Conversation).order_by(Conversation.id).offset(args.offset).limit(args.limit)
        ).all()
        if args.dry_run:
            print(f"[dry-run] selected_conversations={len(conversations)}")
            return

        with output_file.open("w", encoding="utf-8") as output:
            for conversation in conversations:
                if conversation.id is None:
                    continue
                messages = session.exec(
                    select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id)
                ).all()
                payload = {
                    "conversation_id": conversation.id,
                    "thread_id": f"conversation:{conversation.id}",
                    "user_id": conversation.user_id,
                    "messages": [{"role": message.role, "content": message.content} for message in messages],
                }
                output.write(json.dumps(payload) + "\n")
                written += 1
    print(f"wrote {written} conversation payload(s) to {output_file}")


if __name__ == "__main__":
    main()
