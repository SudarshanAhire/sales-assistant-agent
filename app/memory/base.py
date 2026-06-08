from abc import ABC, abstractmethod
from sqlalchemy.orm import Session


class MemoryStore(ABC):
    @abstractmethod
    def get_or_create_user(self, db: Session, user_id: str):
        raise NotImplementedError

    @abstractmethod
    def save_message(self, db: Session, user_id: str, session_id: str, role: str, content: str):
        raise NotImplementedError

    @abstractmethod
    def get_history(self, db: Session, user_id: str):
        raise NotImplementedError

    @abstractmethod
    def add_memory(self, db: Session, user_id: str, fact: str, source_message: str | None = None):
        raise NotImplementedError

    @abstractmethod
    def get_memory(self, db: Session, user_id: str, limit: int = 10):
        raise NotImplementedError

    @abstractmethod
    def wipe_memory(self, db: Session, user_id: str):
        raise NotImplementedError
