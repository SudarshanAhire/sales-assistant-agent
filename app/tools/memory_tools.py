from sqlalchemy.orm import Session
from app.memory.sqlite_store import memory_store


def get_user_memory(db: Session, user_id: str) -> list[str]:
    memories = memory_store.get_memory(db, user_id=user_id, limit=10)
    return [memory.fact for memory in memories]


def save_user_interest(db: Session, user_id: str, message: str) -> None:
    lowered = message.lower()
    keywords = ["starter", "growth", "enterprise", "pricing", "price", "sso", "audit", "sla", "webhooks"]
    found = [keyword for keyword in keywords if keyword in lowered]
    if found:
        fact = f"User previously asked about: {', '.join(sorted(set(found)))}. Original message: {message}"
        memory_store.add_memory(db, user_id=user_id, fact=fact, source_message=message)
