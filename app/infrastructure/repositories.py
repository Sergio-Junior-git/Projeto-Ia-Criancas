from app.infrastructure.db.database import db
from app.infrastructure.db.models import ActivityLogModel, ProgressModel, UserModel


class UserRepository:
    def get_by_email(self, email):
        return UserModel.query.filter_by(email=email.lower().strip()).first()

    def get_by_id(self, user_id):
        return db.session.get(UserModel, user_id)

    def create(self, name, email, password_hash):
        user = UserModel(name=name.strip(), email=email.lower().strip(), password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        return user


class ProgressRepository:
    def get_or_create(self, user_id, discipline, level, topic):
        progress = ProgressModel.query.filter_by(
            user_id=user_id,
            discipline=discipline,
            level=level,
            topic=topic,
        ).first()
        if progress:
            return progress

        progress = ProgressModel(
            user_id=user_id,
            discipline=discipline,
            level=level,
            topic=topic,
            difficulty=1,
        )
        db.session.add(progress)
        db.session.commit()
        return progress

    def list_for_user(self, user_id):
        return ProgressModel.query.filter_by(user_id=user_id).order_by(ProgressModel.updated_at.desc()).all()

    def save_result(self, progress, is_correct):
        if is_correct:
            progress.correct_count += 1
            progress.difficulty = min(progress.difficulty + 1, 5)
        else:
            progress.wrong_count += 1
            if progress.wrong_count % 2 == 0:
                progress.difficulty = max(progress.difficulty - 1, 1)
        db.session.commit()
        return progress

    def reset_for_user(self, user_id):
        ProgressModel.query.filter_by(user_id=user_id).delete()
        db.session.commit()


class ActivityLogRepository:
    def create_question(
        self,
        user_id,
        request_id,
        discipline,
        level,
        topic,
        difficulty,
        question,
        expected_answer,
        explanation=None,
    ):
        log = ActivityLogModel(
            user_id=user_id,
            request_id=request_id,
            discipline=discipline,
            level=level,
            topic=topic,
            difficulty=difficulty,
            question=question,
            expected_answer=expected_answer,
            feedback=explanation,
        )
        db.session.add(log)
        db.session.commit()
        return log

    def get_by_request_id(self, request_id, user_id):
        return ActivityLogModel.query.filter_by(request_id=request_id, user_id=user_id).first()

    def list_questions_for_user_topic(self, user_id, discipline, level, topic):
        rows = (
            ActivityLogModel.query.with_entities(ActivityLogModel.question)
            .filter_by(user_id=user_id, discipline=discipline, level=level, topic=topic)
            .all()
        )
        return [row.question for row in rows]

    def save_answer(self, log, user_answer, is_correct, feedback):
        log.user_answer = user_answer
        log.is_correct = is_correct
        log.feedback = feedback
        db.session.commit()
        return log
