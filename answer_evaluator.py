from typing import Dict
from app import evaluate_answer_internal


def evaluate_objection_handling(session_id: int, question: Dict, user_answer: str, category: str) -> Dict:
    return evaluate_answer_internal(session_id=session_id, question=question, user_answer=user_answer, category=category)

