"""Tests de la connexion Google OAuth (les appels à Google sont simulés)."""
import json
from urllib.parse import parse_qs, urlparse

import pytest


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture()
def gclient(tmp_path, monkeypatch):
    monkeypatch.setenv("EMSP_SECRET_KEY", "test-secret-key")
    monkeypatch.chdir(tmp_path)
    import app as app_module
    app = app_module.app
    app.config.update(
        TESTING=True,
        DATABASE=str(tmp_path / "test.sqlite3"),
        WTF_CSRF_ENABLED=True,
        GOOGLE_CLIENT_ID="client-id-test",
        GOOGLE_CLIENT_SECRET="secret-test",
        GOOGLE_REDIRECT_URI="https://emsp.example/login/google/authorized",
    )
    with app.app_context():
        app_module.init_db()
    with app.test_client() as c:
        yield c, app_module


def start_flow(client):
    response = client.get("/login/google")
    assert response.status_code == 302
    return parse_qs(urlparse(response.headers["Location"]).query)["state"][0]


def fake_google(monkeypatch, app_module, profile):
    monkeypatch.setattr(app_module.requests, "post", lambda *a, **k: FakeResponse(200, {"access_token": "tok"}))
    monkeypatch.setattr(app_module.requests, "get", lambda *a, **k: FakeResponse(200, profile))


def test_button_shown_on_login_and_signup(gclient):
    client, _ = gclient
    for path in ("/connexion", "/inscription"):
        assert "Continuer avec Google" in client.get(path).get_data(as_text=True)


def test_not_configured_redirects_back(gclient):
    client, app_module = gclient
    app_module.app.config.update(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="")
    response = client.get("/login/google")
    assert response.headers["Location"].endswith("/connexion")
    assert "Continuer avec Google" not in client.get("/connexion").get_data(as_text=True)


def test_redirect_to_google_carries_state_and_uri(gclient):
    client, _ = gclient
    response = client.get("/login/google")
    location = response.headers["Location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=client-id-test" in location and "state=" in location
    assert "https%3A//emsp.example/login/google/authorized" in location


def test_invalid_state_is_rejected(gclient):
    client, _ = gclient
    start_flow(client)
    response = client.get("/login/google/authorized?code=abc&state=faux")
    assert response.headers["Location"].endswith("/connexion")
    with client.session_transaction() as sess:
        assert "candidate_id" not in sess


def test_unverified_email_is_rejected(gclient, monkeypatch):
    client, app_module = gclient
    fake_google(monkeypatch, app_module, {"email": "x@example.org", "verified_email": False})
    state = start_flow(client)
    response = client.get(f"/login/google/authorized?code=abc&state={state}")
    assert response.headers["Location"].endswith("/connexion")
    with client.session_transaction() as sess:
        assert "candidate_id" not in sess
    with app_module.app.app_context():
        assert app_module.get_db().execute("SELECT COUNT(*) FROM candidats").fetchone()[0] == 0


def test_verified_email_creates_account_then_reuses_it(gclient, monkeypatch):
    client, app_module = gclient
    fake_google(monkeypatch, app_module, {"email": "Awa@Example.org", "verified_email": True})
    for _ in range(2):
        state = start_flow(client)
        response = client.get(f"/login/google/authorized?code=abc&state={state}")
        assert response.headers["Location"].endswith("/candidature")
        with client.session_transaction() as sess:
            assert sess["candidate_id"]
    with app_module.app.app_context():
        assert app_module.get_db().execute("SELECT COUNT(*) FROM candidats WHERE lower(email)='awa@example.org'").fetchone()[0] == 1


def test_token_exchange_includes_client_secret(gclient, monkeypatch):
    client, app_module = gclient
    captured = {}

    def fake_post(_url, data, **_kwargs):
        captured.update(data)
        return FakeResponse(200, {"access_token": "tok"})

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(
        app_module.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            200, {"email": "awa@example.org", "verified_email": True}
        ),
    )

    state = start_flow(client)
    response = client.get(f"/login/google/authorized?code=abc&state={state}")

    assert response.headers["Location"].endswith("/candidature")
    assert captured["client_secret"] == "secret-test"


def test_google_unreachable_is_handled(gclient, monkeypatch):
    client, app_module = gclient

    def boom(*a, **k):
        raise app_module.requests.ConnectionError("réseau coupé")

    monkeypatch.setattr(app_module.requests, "post", boom)
    state = start_flow(client)
    response = client.get(f"/login/google/authorized?code=abc&state={state}")
    assert response.status_code == 302 and response.headers["Location"].endswith("/connexion")
