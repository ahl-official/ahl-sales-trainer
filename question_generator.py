from typing import Dict
from app import prepare_questions_internal_v3


def generate_questions_from_content(session_id: int, category: str, difficulty: str) -> Dict:
    return prepare_questions_internal_v3(session_id=session_id, category=category, difficulty=difficulty)

