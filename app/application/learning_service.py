import time
import uuid


class LearningService:
    def __init__(self, progress_repository, log_repository, ai_provider):
        self.progress_repository = progress_repository
        self.log_repository = log_repository
        self.ai_provider = ai_provider

    def explanation(self, discipline, level, topic):
        return self.ai_provider.generate_explanation(discipline, level, topic)

    def generate_activity(self, user_id, discipline, level, topic):
        started_at = time.perf_counter()
        progress = self.progress_repository.get_or_create(user_id, discipline, level, topic)
        seen_questions = set(
            self.log_repository.list_questions_for_user_topic(user_id, discipline, level, topic)
        )
        activity = self.ai_provider.generate_activity(
            discipline,
            level,
            topic,
            progress.difficulty,
            list(seen_questions),
        )

        request_id = uuid.uuid4().hex

        self.log_repository.create_question(
            user_id=user_id,
            request_id=request_id,
            discipline=discipline,
            level=level,
            topic=topic,
            difficulty=progress.difficulty,
            question=activity["question"],
            expected_answer=activity["expected_answer"],
            explanation=activity.get("explanation"),
        )

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        activity.pop("expected_answer")
        activity.pop("explanation", None)
        activity.update(
            {
                "request_id": request_id,
                "difficulty": progress.difficulty,
                "latency_ms": latency_ms,
            }
        )
        return activity

    def answer_activity(self, user_id, request_id, user_answer):
        log = self.log_repository.get_by_request_id(request_id, user_id)
        if not log:
            raise ValueError("Questao nao encontrada. Gere uma nova atividade.")

        is_correct, feedback = self.ai_provider.evaluate(
            log.expected_answer,
            user_answer,
            log.discipline,
            log.topic,
        )
        if log.feedback:
            if is_correct:
                feedback = f"Resposta certa! {log.feedback}"
            else:
                feedback = f"A resposta esperada era '{log.expected_answer}'. {log.feedback}"
        self.log_repository.save_answer(log, user_answer, is_correct, feedback)

        progress = self.progress_repository.get_or_create(
            user_id,
            log.discipline,
            log.level,
            log.topic,
        )
        self.progress_repository.save_result(progress, is_correct)

        return {
            "correct": is_correct,
            "expected_answer": log.expected_answer,
            "feedback": feedback,
            "next_difficulty": progress.difficulty,
            "can_retry": not is_correct,
        }
