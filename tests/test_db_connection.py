from app import create_app
from app.infrastructure.db.database import db


def run():
    app = create_app()
    with app.app_context():
        print("[database] Teste manual OK. Engine conectada e aplicacao carregada.")
        print(f"[database] Driver: {db.engine.driver}")


if __name__ == "__main__":
    run()
