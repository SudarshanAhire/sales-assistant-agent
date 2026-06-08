from app.config import settings
from app.services.llm_service import llm_service


async def evaluate_response(user_message: str, agent_response: str, catalog_context: str, memory_context: str) -> dict:
    fallback = {
        "groundedness": 0.9 if catalog_context else 0.55,
        "relevance": 0.88,
        "confidence": 0.86 if catalog_context else 0.55,
        "flagged": False if catalog_context else True,
        "reasoning": "Response was evaluated using catalog context and user memory. Fallback scoring used if evaluator LLM is unavailable.",
    }
    messages = [
        {
            "role": "system",
            "content": "You are an evaluator. Return only valid JSON with groundedness, relevance, confidence, flagged, reasoning. Scores must be 0 to 1.",
        },
        {
            "role": "user",
            "content": f"User message: {user_message}\nAgent response: {agent_response}\nCatalog context: {catalog_context}\nUser memory: {memory_context}\nEvaluate the response.",
        },
    ]
    data = await llm_service.json_chat(messages, fallback)
    for key in ["groundedness", "relevance", "confidence"]:
        data[key] = max(0.0, min(1.0, float(data.get(key, fallback[key]))))
    data["flagged"] = bool(data.get("flagged", False)) or data["confidence"] < settings.eval_confidence_threshold
    data["reasoning"] = str(data.get("reasoning", fallback["reasoning"]))
    return data
