from sqlalchemy.orm import Session
from app.db.models import EvalLog, Memory, Message, User
from app.memory.base import MemoryStore


class SQLiteMemoryStore(MemoryStore):
    def get_or_create_user(self, db: Session, user_id: str) -> User:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            return user
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def save_message(self, db: Session, user_id: str, session_id: str, role: str, content: str) -> Message:
        user = self.get_or_create_user(db, user_id)
        msg = Message(user_pk=user.id, session_id=session_id, role=role, content=content)
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def get_history(self, db: Session, user_id: str) -> list[Message]:
        user = self.get_or_create_user(db, user_id)
        return db.query(Message).filter(Message.user_pk == user.id).order_by(Message.created_at.asc()).all()

    def add_memory(self, db: Session, user_id: str, fact: str, source_message: str | None = None) -> Memory:
        user = self.get_or_create_user(db, user_id)
        existing = db.query(Memory).filter(Memory.user_pk == user.id, Memory.fact == fact).first()
        if existing:
            return existing
        memory = Memory(user_pk=user.id, fact=fact, source_message=source_message)
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory

    def get_memory(self, db: Session, user_id: str, limit: int = 10) -> list[Memory]:
        user = self.get_or_create_user(db, user_id)
        return db.query(Memory).filter(Memory.user_pk == user.id).order_by(Memory.created_at.desc()).limit(limit).all()

    def wipe_memory(self, db: Session, user_id: str) -> None:
        user = self.get_or_create_user(db, user_id)
        db.query(Memory).filter(Memory.user_pk == user.id).delete()
        db.commit()

    def log_eval(self, db: Session, user_id: str, session_id: str, response: str, eval_data: dict) -> EvalLog:
        user = self.get_or_create_user(db, user_id)
        log = EvalLog(
            user_pk=user.id,
            session_id=session_id,
            response=response,
            groundedness=float(eval_data["groundedness"]),
            relevance=float(eval_data["relevance"]),
            confidence=float(eval_data["confidence"]),
            flagged=bool(eval_data["flagged"]),
            reasoning=eval_data["reasoning"],
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log


memory_store = SQLiteMemoryStore()
