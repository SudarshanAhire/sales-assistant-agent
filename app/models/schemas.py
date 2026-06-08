from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class EvalBlock(BaseModel):
    groundedness: float
    relevance: float
    confidence: float
    flagged: bool
    reasoning: str


class ChatResponse(BaseModel):
    response: str
    eval: EvalBlock
    tools_called: list[str]
    session_id: str


class MessageItem(BaseModel):
    role: str
    content: str
    session_id: str
    created_at: datetime


class HistoryResponse(BaseModel):
    user_id: str
    history: list[MessageItem]


class MemoryDeleteResponse(BaseModel):
    user_id: str
    deleted: bool
    message: str


class HealthResponse(BaseModel):
    status: str


class EvalAggregateResponse(BaseModel):
    user_id: str
    total_responses: int
    average_groundedness: float
    average_relevance: float
    average_confidence: float
    high_confidence_percentage: float
    flagged_count: int
