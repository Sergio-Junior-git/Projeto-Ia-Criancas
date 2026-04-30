import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os

from app.application.ai_provider import GroqLearningAI


def run():
    load_dotenv()
    provider = os.getenv("AI_PROVIDER", "groq").strip().lower()
    print(f"[ai] Testando provider: {provider}")
    ai = GroqLearningAI()
    seen = []
    for difficulty in [1, 3, 5]:
        activity = ai.generate_activity(
            discipline="ingles",
            level="fundamental_1",
            topic="rotina",
            difficulty=difficulty,
            excluded_questions=seen,
        )
        seen.append(activity["question"])
        print(f"[ai] Dificuldade {difficulty}: {activity}")
    print("[ai] Teste Groq OK.")


if __name__ == "__main__":
    run()
