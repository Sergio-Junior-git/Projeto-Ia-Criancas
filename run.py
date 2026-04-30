import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=debug, use_reloader=debug)
