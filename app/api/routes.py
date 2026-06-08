from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models import EvalLog
from app.memory.sqlite_store import memory_store
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    EvalAggregateResponse,
    HealthResponse,
    HistoryResponse,
    MemoryDeleteResponse,
    MessageItem,
)
from app.services.chat_service import handle_chat
from app.tools.catalog_tools import load_catalog

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@router.get("/catalog")
def catalog():
    return load_catalog()


@router.post("/chat/{user_id}", response_model=ChatResponse)
async def chat(user_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    return await handle_chat(db, user_id, payload.message, payload.session_id)


@router.get("/chat/{user_id}/history", response_model=HistoryResponse)
def history(user_id: str, db: Session = Depends(get_db)):
    messages = memory_store.get_history(db, user_id)
    return {
        "user_id": user_id,
        "history": [
            MessageItem(
                role=m.role,
                content=m.content,
                session_id=m.session_id,
                created_at=m.created_at,
            )
            for m in messages
        ],
    }


@router.delete("/chat/{user_id}/memory", response_model=MemoryDeleteResponse)
def delete_memory(user_id: str, db: Session = Depends(get_db)):
    memory_store.wipe_memory(db, user_id)
    return {
        "user_id": user_id,
        "deleted": True,
        "message": "User memory wiped successfully. Conversation history and eval logs are retained for audit unless you extend this endpoint.",
    }


@router.get("/chat/{user_id}/evals", response_model=EvalAggregateResponse)
def evals(user_id: str, db: Session = Depends(get_db)):
    user = memory_store.get_or_create_user(db, user_id)
    total = db.query(EvalLog).filter(EvalLog.user_pk == user.id).count()
    if total == 0:
        return {
            "user_id": user_id,
            "total_responses": 0,
            "average_groundedness": 0,
            "average_relevance": 0,
            "average_confidence": 0,
            "high_confidence_percentage": 0,
            "flagged_count": 0,
        }

    avg_groundedness, avg_relevance, avg_confidence = db.query(
        func.avg(EvalLog.groundedness),
        func.avg(EvalLog.relevance),
        func.avg(EvalLog.confidence),
    ).filter(EvalLog.user_pk == user.id).one()

    high_conf = db.query(EvalLog).filter(EvalLog.user_pk == user.id, EvalLog.confidence >= 0.8).count()
    flagged = db.query(EvalLog).filter(EvalLog.user_pk == user.id, EvalLog.flagged.is_(True)).count()

    return {
        "user_id": user_id,
        "total_responses": total,
        "average_groundedness": round(float(avg_groundedness), 3),
        "average_relevance": round(float(avg_relevance), 3),
        "average_confidence": round(float(avg_confidence), 3),
        "high_confidence_percentage": round((high_conf / total) * 100, 2),
        "flagged_count": flagged,
    }
