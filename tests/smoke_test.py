import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.config import Config


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(tempfile.gettempdir()) / 'hospital_estudos_test.db'}"


def extract_csrf(html):
    hidden = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if hidden:
        return hidden.group(1)
    meta = re.search(r'meta name="csrf-token" content="([^"]+)"', html)
    if meta:
        return meta.group(1)
    raise AssertionError("CSRF token nao encontrado")


def run():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/cadastro")
    csrf = extract_csrf(response.text)

    response = client.post(
        "/cadastro",
        data={
            "csrf_token": csrf,
            "name": "Aluno Teste",
            "email": "aluno@example.com",
            "password": "123456",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Escolha uma disciplina" in response.text

    csrf = extract_csrf(response.text)
    response = client.post(
        "/api/activity/generate",
        json={"discipline": "matematica", "level": "fundamental_1", "topic": "operacoes"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    activity = response.get_json()
    assert activity["request_id"]
    assert activity["question"]

    response = client.post(
        "/api/activity/answer",
        json={"request_id": activity["request_id"], "answer": "0"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    result = response.get_json()
    assert "feedback" in result
    assert "next_difficulty" in result

    response = client.get("/api/progress")
    assert response.status_code == 200
    assert len(response.get_json()) == 1

    print("smoke test ok")


if __name__ == "__main__":
    run()
