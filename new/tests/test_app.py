import io

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EMSP_SECRET_KEY", "test-secret-key")
    from app import app
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "test.sqlite3"), WTF_CSRF_ENABLED=True)
    with app.app_context():
        from app import init_db
        init_db()
    with app.test_client() as test_client:
        yield test_client


def token(client, path):
    response = client.get(path)
    html = response.get_data(as_text=True)
    marker = 'name="csrf_token" value="'
    return html.split(marker, 1)[1].split('"', 1)[0]


def test_csrf_and_auth_flow(client):
    response = client.post("/inscription", data={"email": "a@example.org"})
    assert response.status_code == 400
    csrf = token(client, "/inscription")
    response = client.post("/inscription", data={"csrf_token": csrf, "nom": "A", "prenoms": "B", "telephone": "0700000000", "email": "a@example.org", "password": "password123", "password_confirmation": "password123"})
    assert response.status_code == 302
    assert client.get("/candidature").status_code == 302


def test_rejects_executable_upload(client):
    csrf = token(client, "/inscription")
    client.post("/inscription", data={"csrf_token": csrf, "nom": "A", "prenoms": "B", "telephone": "0700000000", "email": "b@example.org", "password": "password123", "password_confirmation": "password123"})
    csrf = token(client, "/connexion")
    client.post("/connexion", data={"csrf_token": csrf, "identifiant": "b@example.org", "password": "password123"})
    csrf = token(client, "/candidature")
    response = client.post("/candidature", data={"csrf_token": csrf, "action": "brouillon", "photo": (io.BytesIO(b"MZ"), "virus.exe")}, content_type="multipart/form-data")
    assert response.status_code == 302


def test_private_files_are_not_exposed(client):
    assert client.get("/app.py").status_code == 404
    assert client.get("/schema.sql").status_code == 404
    assert client.get("/uploads/test").status_code == 404


def test_server_generates_application_number(client):
    csrf = token(client, "/inscription")
    response = client.post("/inscription", data={"csrf_token": csrf, "nom": "Serveur", "prenoms": "Numero", "telephone": "0700000000", "email": "number@example.org", "password": "password123", "password_confirmation": "password123"})
    assert response.status_code == 302
    csrf = token(client, "/connexion")
    client.post("/connexion", data={"csrf_token": csrf, "identifiant": "number@example.org", "password": "password123"})
    assert b"EMSP-" in client.get("/candidature").data


def test_admin_can_edit_profile_and_log_out(client):
    from app import get_db, now
    from werkzeug.security import generate_password_hash

    with client.application.app_context():
        cursor = get_db().execute(
            "INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            ("EMSP-ADMIN-TEST", "admin@example.org", generate_password_hash("password123"), "Admin", "Test", "0700000000", now()),
        )
        get_db().commit()
        admin_id = cursor.lastrowid

    with client.session_transaction() as session:
        session["candidate_id"] = admin_id

    response = client.get("/profil")
    assert response.status_code == 200
    csrf = token(client, "/profil")
    response = client.post("/profil", data={
        "csrf_token": csrf,
        "nom": "Admin modifié",
        "prenoms": "Test",
        "telephone": "0700000001",
        "email": "admin@example.org",
    })
    assert response.status_code == 302

    with client.application.app_context():
        candidate = get_db().execute("SELECT nom, telephone FROM candidats WHERE id = ?", (admin_id,)).fetchone()
        assert candidate["nom"] == "Admin modifié"
        assert candidate["telephone"] == "0700000001"

    csrf = token(client, "/admin")
    response = client.post("/deconnexion", data={"csrf_token": csrf})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/connexion")


def test_admin_physical_folder_pages_have_navigation(client, tmp_path):
    from app import get_db, now
    from werkzeug.security import generate_password_hash

    folder_path = tmp_path / "physical-folder"
    folder_path.mkdir()
    with client.application.app_context():
        cursor = get_db().execute(
            "INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            ("EMSP-ADMIN-FOLDER", "folder-admin@example.org", generate_password_hash("password123"), "Admin", "Dossier", "0700000000", now()),
        )
        get_db().execute(
            "INSERT INTO dossiers_physiques (candidat_id, numero_dossier, chemin_dossier, cree_le) VALUES (?, ?, ?, ?)",
            (cursor.lastrowid, "DOSSIER-TEST", str(folder_path), now()),
        )
        get_db().commit()
        admin_id = cursor.lastrowid

    with client.session_transaction() as session:
        session["candidate_id"] = admin_id

    list_response = client.get("/admin/dossiers-physiques")
    assert list_response.status_code == 200
    assert b"Tableau de bord" in list_response.data
    assert b"Mon profil" in list_response.data
    assert b"D\xc3\xa9connexion" in list_response.data

    detail_response = client.get("/admin/dossiers-physiques/1")
    assert detail_response.status_code == 200
    assert b"Tableau de bord" in detail_response.data
    assert b"Retour \xc3\xa0 la liste" in detail_response.data


def test_admin_candidature_detail_has_navigation(client):
    from app import get_db, now
    from werkzeug.security import generate_password_hash

    with client.application.app_context():
        cursor = get_db().execute(
            "INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            ("EMSP-ADMIN-DETAIL", "detail-admin@example.org", generate_password_hash("password123"), "Admin", "Detail", "0700000000", now()),
        )
        candidature = get_db().execute(
            "INSERT INTO candidatures (candidat_id, created_at, updated_at) VALUES (?, ?, ?)",
            (cursor.lastrowid, now(), now()),
        )
        get_db().commit()
        candidature_id = candidature.lastrowid
        admin_id = cursor.lastrowid

    with client.session_transaction() as session:
        session["candidate_id"] = admin_id

    response = client.get(f"/admin/candidature/{candidature_id}")
    assert response.status_code == 200
    assert b"Tableau de bord" in response.data
    assert b"Retour aux candidatures" in response.data
    assert b"Mon profil" in response.data
    assert b"D\xc3\xa9connexion" in response.data


def test_error_page_uses_auth_layout(client):
    response = client.get("/route-inconnue")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert 'class="auth-shell"' in html
    assert 'css/pages/auth.css' in html
    assert 'css/connexion.css' not in html


def test_candidate_physical_folder_pages_keep_account_navigation(client, tmp_path):
    from app import get_db, now
    from werkzeug.security import generate_password_hash

    folder_path = tmp_path / "candidate-folder"
    folder_path.mkdir()
    with client.application.app_context():
        cursor = get_db().execute(
            "INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("EMSP-CANDIDATE-FOLDER", "candidate-folder@example.org", generate_password_hash("password123"), "Candidat", "Dossier", "0700000000", now()),
        )
        get_db().execute(
            "INSERT INTO dossiers_physiques (candidat_id, numero_dossier, chemin_dossier, cree_le) VALUES (?, ?, ?, ?)",
            (cursor.lastrowid, "DOSSIER-CANDIDAT", str(folder_path), now()),
        )
        get_db().commit()
        candidate_id = cursor.lastrowid

    with client.session_transaction() as session:
        session["candidate_id"] = candidate_id

    list_response = client.get("/dossiers-physiques")
    assert list_response.status_code == 200
    assert b"Mon profil" in list_response.data
    assert b"D\xc3\xa9connexion" in list_response.data

    detail_response = client.get("/dossiers-physiques/1")
    assert detail_response.status_code == 200
    assert b"Mon profil" in detail_response.data
    assert b"D\xc3\xa9connexion" in detail_response.data


def test_password_recovery_page_uses_auth_layout(client):
    response = client.get("/mot-de-passe-oublie")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="auth-shell"' in html
    assert 'class="form-control-custom"' in html
    assert 'css/pages/auth.css' in html
    assert 'css/connexion.css' not in html


def test_password_reset_sends_email_using_smtp_settings(client, monkeypatch):
    import app as app_module
    from app import get_db, now
    from werkzeug.security import generate_password_hash

    with client.application.app_context():
        get_db().execute(
            "INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("EMSP-RESET-TEST", "reset@example.org", generate_password_hash("password123"), "Reset", "Test", "0700000000", now()),
        )
        get_db().commit()

    sent = {}

    def fake_send(recipient, reset_url):
        sent["recipient"] = recipient
        sent["reset_url"] = reset_url

    monkeypatch.setitem(app_module.app.config, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setitem(app_module.app.config, "PUBLIC_BASE_URL", "https://emsp.example.org")
    monkeypatch.setattr(app_module, "send_password_reset_email", fake_send)

    csrf = token(client, "/mot-de-passe-oublie")
    response = client.post("/mot-de-passe-oublie", data={"csrf_token": csrf, "email": "reset@example.org"})

    assert response.status_code == 302
    assert sent["recipient"] == "reset@example.org"
    assert sent["reset_url"].startswith("https://emsp.example.org/reinitialiser-mot-de-passe/")


def test_password_reset_email_uses_starttls_and_authentication(monkeypatch):
    import app as app_module

    events = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context):
            events.append(("starttls", context is not None))

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send", message["To"], message["From"], message["Subject"], message.get_content()))

    monkeypatch.setitem(app_module.app.config, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setitem(app_module.app.config, "SMTP_PORT", 587)
    monkeypatch.setitem(app_module.app.config, "SMTP_USERNAME", "mailer@example.org")
    monkeypatch.setitem(app_module.app.config, "SMTP_PASSWORD", "test-password")
    monkeypatch.setitem(app_module.app.config, "SMTP_SENDER", "no-reply@example.org")
    monkeypatch.setitem(app_module.app.config, "SMTP_USE_TLS", True)
    monkeypatch.setitem(app_module.app.config, "SMTP_USE_SSL", False)
    monkeypatch.setattr(app_module.smtplib, "SMTP", FakeSMTP)

    app_module.send_password_reset_email("candidate@example.org", "https://emsp.example.org/reset/token")

    assert ("connect", "smtp.example.org", 587, 15) in events
    assert any(event[0] == "starttls" and event[1] for event in events)
    assert ("login", "mailer@example.org", "test-password") in events
    sent_message = next(event for event in events if event[0] == "send")
    assert sent_message[1] == "candidate@example.org"
    assert sent_message[2] == "no-reply@example.org"
    assert "https://emsp.example.org/reset/token" in sent_message[4]
