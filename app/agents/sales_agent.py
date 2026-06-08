import json
from sqlalchemy.orm import Session
from app.services.llm_service import llm_service
from app.services.eval_service import evaluate_response
from app.tools.catalog_tools import search_catalog
from app.tools.memory_tools import get_user_memory, save_user_interest
from app.tools.human_tools import flag_for_human


async def run_sales_agent(db: Session, user_id: str, user_message: str) -> dict:
    tools_called: list[str] = []

    memory = get_user_memory(db, user_id)
    tools_called.append("get_user_memory")

    catalog_results = search_catalog(user_message + " " + " ".join(memory))
    tools_called.append("search_catalog")

    catalog_context = json.dumps(catalog_results, indent=2)
    memory_context = "\n".join(memory) if memory else "No stored user memory yet."

    messages = [
        {
            "role": "system",
            "content": (
                "You are a B2B SaaS sales assistant. Answer only using the supplied catalog context and user memory. "
                "If information is not in the catalog, say you do not know. Be concise and helpful."
            ),
        },
        {
            "role": "user",
            "content": f"Catalog context:\n{catalog_context}\n\nUser memory:\n{memory_context}\n\nUser question:\n{user_message}",
        },
    ]

    response = await llm_service.chat(messages)
    eval_data = await evaluate_response(user_message, response, catalog_context, memory_context)

    if eval_data["flagged"]:
        flag_for_human(user_id, eval_data["reasoning"])
        tools_called.append("flag_for_human")

    save_user_interest(db, user_id, user_message)

    return {
        "response": response,
        "eval": eval_data,
        "tools_called": tools_called,
    }
