import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog.json"


def load_catalog() -> dict[str, Any]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def search_catalog(query: str) -> list[dict[str, Any]]:
    """Keyword search over catalog.json. Replace with embeddings/vector search at scale."""
    catalog = load_catalog()
    query_terms = set(query.lower().replace("?", "").replace(",", "").split())
    results: list[dict[str, Any]] = []

    for plan in catalog.get("plans", []):
        searchable = " ".join([
            plan.get("name", ""),
            plan.get("price", ""),
            plan.get("best_for", ""),
            " ".join(plan.get("features", [])),
        ]).lower()
        score = sum(1 for term in query_terms if term in searchable)
        if score > 0:
            item = dict(plan)
            item["match_score"] = score
            results.append(item)

    if not results:
        return catalog.get("plans", [])

    return sorted(results, key=lambda x: x["match_score"], reverse=True)
