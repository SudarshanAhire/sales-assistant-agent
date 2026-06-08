from uuid import uuid4
from sqlalchemy.orm import Session
from app.agents.sales_agent import run_sales_agent
from app.memory.sqlite_store import memory_store


async def handle_chat(db: Session, user_id: str, message: str, session_id: str | None = None) -> dict:
    session_id = session_id or str(uuid4())
    memory_store.save_message(db, user_id, session_id, "user", message)

    result = await run_sales_agent(db, user_id, message)

    memory_store.save_message(db, user_id, session_id, "assistant", result["response"])
    memory_store.log_eval(db, user_id, session_id, result["response"], result["eval"])

    return {
        "response": result["response"],
        "eval": result["eval"],
        "tools_called": result["tools_called"],
        "session_id": session_id,
    }
