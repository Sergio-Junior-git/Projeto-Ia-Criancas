import os
from functools import lru_cache
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.application.ai_provider import FallbackLearningAI, GroqLearningAI, LocalLearningAI
from app.application.learning_service import LearningService
from app.application.security import ensure_csrf_token, validate_csrf
from app.application.user_service import UserService
from app.domain.catalog import DISCIPLINES, SCHOOL_LEVELS, TOPICS
from app.infrastructure.repositories import ActivityLogRepository, ProgressRepository, UserRepository


web_bp = Blueprint("web", __name__)


@lru_cache(maxsize=1)
def ai_provider():
    provider = os.getenv("AI_PROVIDER", "local").strip().lower()
    local = LocalLearningAI()
    if provider == "groq":
        try:
            print("[ai] Usando Groq para gerar atividades.")
            return FallbackLearningAI(GroqLearningAI(), local)
        except ValueError as exc:
            print(f"[ai] Groq nao configurado. Usando gerador local: {exc}")
    return local


def services():
    users = UserRepository()
    progress = ProgressRepository()
    logs = ActivityLogRepository()
    return {
        "users": UserService(users),
        "learning": LearningService(progress, logs, ai_provider()),
        "progress": progress,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("web.login"))
        return view(*args, **kwargs)

    return wrapped


@web_bp.app_context_processor
def inject_globals():
    return {"csrf_token": ensure_csrf_token(), "disciplines": DISCIPLINES, "levels": SCHOOL_LEVELS}


@web_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Sessao expirada. Tente novamente.", "error")
            return redirect(url_for("web.login"))
        try:
            user = services()["users"].authenticate(request.form["email"], request.form["password"])
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            ensure_csrf_token()
            return redirect(url_for("web.dashboard"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("login.html")


@web_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Sessao expirada. Tente novamente.", "error")
            return redirect(url_for("web.register"))
        try:
            user = services()["users"].register(
                request.form["name"],
                request.form["email"],
                request.form["password"],
            )
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            ensure_csrf_token()
            return redirect(url_for("web.dashboard"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("register.html")


@web_bp.route("/sair")
def logout():
    session.clear()
    return redirect(url_for("web.login"))


@web_bp.route("/dashboard")
@login_required
def dashboard():
    progress_items = services()["progress"].list_for_user(session["user_id"])
    return render_template("dashboard.html", progress_items=progress_items)


@web_bp.route("/disciplina/<discipline>")
@login_required
def discipline(discipline):
    if discipline not in DISCIPLINES:
        return redirect(url_for("web.dashboard"))
    return render_template("discipline.html", discipline_key=discipline, topics=TOPICS[discipline])


@web_bp.route("/estudar/<discipline>/<level>/<topic>")
@login_required
def study(discipline, level, topic):
    if discipline not in DISCIPLINES or level not in SCHOOL_LEVELS or topic not in TOPICS[discipline].get(level, []):
        return redirect(url_for("web.dashboard"))

    explanation = services()["learning"].explanation(discipline, level, topic)
    return render_template(
        "study.html",
        discipline_key=discipline,
        level_key=level,
        topic=topic,
        explanation=explanation,
    )


@web_bp.route("/api/activity/generate", methods=["POST"])
@login_required
def api_generate_activity():
    payload = request.get_json(silent=True) or {}
    if not validate_csrf(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Token de seguranca invalido."}), 403
    discipline = payload.get("discipline")
    level = payload.get("level")
    topic = payload.get("topic")
    if discipline not in DISCIPLINES or level not in SCHOOL_LEVELS or topic not in TOPICS.get(discipline, {}).get(level, []):
        return jsonify({"error": "Disciplina, nivel ou assunto invalido."}), 400

    activity = services()["learning"].generate_activity(
        session["user_id"],
        discipline,
        level,
        topic,
    )
    return jsonify(activity)


@web_bp.route("/api/activity/answer", methods=["POST"])
@login_required
def api_answer_activity():
    payload = request.get_json(silent=True) or {}
    if not validate_csrf(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Token de seguranca invalido."}), 403
    try:
        result = services()["learning"].answer_activity(
            session["user_id"],
            payload.get("request_id"),
            payload.get("answer", ""),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@web_bp.route("/api/progress")
@login_required
def api_progress():
    items = services()["progress"].list_for_user(session["user_id"])
    return jsonify(
        [
            {
                "discipline": item.discipline,
                "level": item.level,
                "topic": item.topic,
                "difficulty": item.difficulty,
                "correct": item.correct_count,
                "wrong": item.wrong_count,
            }
            for item in items
        ]
    )


@web_bp.route("/api/reset-progress", methods=["POST"])
@login_required
def api_reset_progress():
    if not validate_csrf(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Token de seguranca invalido."}), 403
    services()["progress"].reset_for_user(session["user_id"])
    return jsonify({"ok": True, "message": "Progresso reiniciado."})
