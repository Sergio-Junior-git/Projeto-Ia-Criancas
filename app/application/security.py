import secrets

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validate_csrf(token):
    return bool(token) and secrets.compare_digest(token, session.get("csrf_token", ""))
