import logging

logger = logging.getLogger("human_review")


def flag_for_human(user_id: str, reason: str) -> bool:
    logger.warning("Human review needed for user=%s reason=%s", user_id, reason)
    return True
