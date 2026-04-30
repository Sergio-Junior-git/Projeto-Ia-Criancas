from flask import Flask
from pymysql.err import OperationalError as PyMySQLOperationalError
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError
from sqlalchemy import inspect, text

from app.config import Config
from app.infrastructure.db.database import db
from app.infrastructure.db import models
from app.presentation.routes import web_bp


def _safe_database_uri(uri):
    if "@" not in uri or "://" not in uri:
        return uri

    scheme, rest = uri.split("://", 1)
    credentials, host = rest.split("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


def _check_database_connection(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    print(f"[database] Usando: {_safe_database_uri(uri)}")

    try:
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        db.create_all()
        tables = inspect(db.engine).get_table_names()
        print(f"[database] Conexao OK. Tabelas disponiveis: {', '.join(tables) or 'nenhuma'}")
    except SQLAlchemyOperationalError as exc:
        db.session.rollback()
        print(f"[database] Falha na conexao ou criacao das tabelas: {exc}")
        if _looks_like_mysql_auth_error(exc):
            print("[database] Dica: confira o DATABASE_URL no formato:")
            print("[database] mysql+pymysql://usuario:senha@host:porta/nome_do_banco?charset=utf8mb4")
            print("[database] Exemplo: mysql+pymysql://root:minhasenha@127.0.0.1:3306/db_projetoiacrianca?charset=utf8mb4")
        raise
    except Exception as exc:
        db.session.rollback()
        print(f"[database] Falha na conexao ou criacao das tabelas: {exc}")
        raise


def _looks_like_mysql_auth_error(exc):
    original = getattr(exc, "orig", None)
    if isinstance(original, PyMySQLOperationalError) and original.args:
        return original.args[0] == 1045
    return False


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="presentation/templates",
        static_folder="presentation/static",
    )
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(web_bp)

    with app.app_context():
        _check_database_connection(app)

    return app
