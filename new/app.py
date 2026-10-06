from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import base64
import csv
import hashlib
import io
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    g,
    json,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
import click
from flask_wtf import CSRFProtect
import requests
from werkzeug.security import check_password_hash, generate_password_hash

from utils import creer_dossier_utilisateur


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "private_uploads"
SCHEMA_FILE = BASE_DIR / "schema.sql"
INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
configured_secret = os.environ.get("EMSP_SECRET_KEY")
if not configured_secret and os.environ.get("FLASK_DEBUG", "0") != "1":
    raise RuntimeError("EMSP_SECRET_KEY doit être défini hors mode debug.")
app.config.update(
    DEBUG=os.environ.get("FLASK_DEBUG", "0") == "1",
    SECRET_KEY=configured_secret or secrets.token_hex(32),
    DATABASE=str(INSTANCE_DIR / "emsp.sqlite3"),
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_DEBUG", "0") != "1",
    CONTACT_EMAIL=os.environ.get("CONTACT_EMAIL", "contact@emsp.ci"),
    CONTACT_PHONE=os.environ.get("CONTACT_PHONE", "+225 27 21 21 45 60"),
    CONTACT_SECRETARIAT=os.environ.get("CONTACT_SECRETARIAT", ""),
    CONTACT_GEO_ADDRESS=os.environ.get("CONTACT_GEO_ADDRESS", ""),
    CONTACT_POSTAL_ADDRESS=os.environ.get("CONTACT_POSTAL_ADDRESS", ""),
    CONTACT_OPENING_HOURS=os.environ.get("CONTACT_OPENING_HOURS", ""),
    CONTACT_WEBSITE=os.environ.get("CONTACT_WEBSITE", ""),
    SMTP_HOST=os.environ.get("SMTP_HOST", "").strip(),
    SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
    SMTP_USERNAME=os.environ.get("SMTP_USERNAME", ""),
    SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
    SMTP_SENDER=os.environ.get("SMTP_SENDER", ""),
    SMTP_USE_TLS=os.environ.get("SMTP_USE_TLS", "1").lower() in {"1", "true", "yes", "on"},
    SMTP_USE_SSL=os.environ.get("SMTP_USE_SSL", "0").lower() in {"1", "true", "yes", "on"},
    PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "").rstrip("/"),
    GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID", ""),
    GOOGLE_CLIENT_SECRET=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    GOOGLE_REDIRECT_URI=os.environ.get("GOOGLE_REDIRECT_URI") or ((os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") + "/login/google/authorized") if os.environ.get("PUBLIC_BASE_URL", "").strip() else "http://localhost:5000/login/google/authorized"),
)
csrf = CSRFProtect(app)

log_path = BASE_DIR / "logs" / "google_oauth.log"
log_path.parent.mkdir(parents=True, exist_ok=True)
google_logger = logging.getLogger("google_oauth")
google_logger.setLevel(logging.INFO)
if not google_logger.handlers:
    handler = RotatingFileHandler(log_path, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    handler.flush = lambda: None
    google_logger.addHandler(handler)
    google_logger.propagate = False

if not app.config.get("GOOGLE_CLIENT_ID"):
    app.logger.warning("GOOGLE_CLIENT_ID est vide. La connexion Google sera désactivée.")
if not app.config.get("GOOGLE_REDIRECT_URI"):
    app.logger.warning("GOOGLE_REDIRECT_URI est vide. La connexion Google pourrait échouer.")

ALLOWED_FIELDS = (
    "code_tresor_pay", "nom", "prenoms", "sexe", "date_naissance",
    "lieu_naissance", "nationalite", "telephone", "nature_piece",
    "numero_piece", "commune", "ville", "adresse", "annee_bac",
    "serie_bac", "numero_bac", "numero_table", "mention", "moyenne_bac",
    "note_math_bac", "note_physique_bac", "note_francais_bac", "note_anglais_bac",
    "choix_1_filiere", "choix_2_filiere", "tuteur1_nom", "tuteur1_contact",
    "tuteur1_lien", "tuteur1_residence", "tuteur2_nom", "tuteur2_contact",
    "tuteur2_lien", "tuteur2_residence",
)
FILE_FIELDS = (
    "photo", "cni", "acte_naissance", "attestation", "releve_bac",
    "bulletins_seconde", "bulletins_premiere", "bulletins_terminale",
    "cv", "lettre_motivation",
)
FILIERES = (
    "Digitalisation des services",
    "Finance digitale",
    "Logistique numérique",
    "Marketing digital",
    "Gestion des activités réglementée de l'économie",
)
NATURES_PIECE = ("CNI", "ATTESTATION", "PASSEPORT", "CONSULAIRE")
MAGIC_BYTES = {
    "pdf": (b"%PDF",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}
login_failures: dict[tuple[str, str], list[datetime]] = {}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    with app.app_context():
        get_db().executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        get_db().commit()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    host = app.config["SMTP_HOST"]
    if not host:
        raise RuntimeError("SMTP_HOST n'est pas configuré.")

    sender = app.config["SMTP_SENDER"] or app.config["SMTP_USERNAME"]
    if not sender:
        raise RuntimeError("SMTP_SENDER n'est pas configuré.")

    message = EmailMessage()
    message["Subject"] = "Réinitialisation de votre mot de passe EMSP"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Bonjour,\n\n"
        "Une demande de réinitialisation du mot de passe de votre compte EMSP a été reçue.\n"
        "Utilisez le lien ci-dessous dans l'heure qui suit :\n\n"
        f"{reset_url}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer ce message.\n\n"
        "L'équipe EMSP"
    )

    context = ssl.create_default_context()
    if app.config["SMTP_USE_SSL"]:
        connection = smtplib.SMTP_SSL(host, app.config["SMTP_PORT"], timeout=15, context=context)
    else:
        connection = smtplib.SMTP(host, app.config["SMTP_PORT"], timeout=15)

    with connection as server:
        if not app.config["SMTP_USE_SSL"] and app.config["SMTP_USE_TLS"]:
            server.starttls(context=context)
        if app.config["SMTP_USERNAME"]:
            server.login(app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"])
        server.send_message(message)


def send_email(recipient: str, subject: str, body: str) -> None:
    host = app.config["SMTP_HOST"]
    if not host:
        return

    sender = app.config["SMTP_SENDER"] or app.config["SMTP_USERNAME"]
    if not sender:
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    context = ssl.create_default_context()
    if app.config["SMTP_USE_SSL"]:
        connection = smtplib.SMTP_SSL(host, app.config["SMTP_PORT"], timeout=15, context=context)
    else:
        connection = smtplib.SMTP(host, app.config["SMTP_PORT"], timeout=15)

    with connection as server:
        if not app.config["SMTP_USE_SSL"] and app.config["SMTP_USE_TLS"]:
            server.starttls(context=context)
        if app.config["SMTP_USERNAME"]:
            server.login(app.config["SMTP_USERNAME"], app.config["SMTP_PASSWORD"])
        server.send_message(message)


def current_candidate() -> sqlite3.Row | None:
    candidate_id = session.get("candidate_id")
    if not candidate_id:
        return None
    return get_db().execute("SELECT * FROM candidats WHERE id = ?", (candidate_id,)).fetchone()


def safe_next(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return None
    return value


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_candidate() is None:
            next_url = request.path if request.query_string == b"" else request.full_path.rstrip("?")
            flash("Connectez-vous pour accéder à cet espace.", "warning")
            return redirect(url_for("connexion", next=next_url))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_candidate()["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def dossier_number() -> str:
    while True:
        value = f"EMSP-{datetime.now():%Y}-{secrets.randbelow(90000) + 10000}"
        if get_db().execute("SELECT 1 FROM candidats WHERE numero_dossier = ?", (value,)).fetchone() is None:
            return value


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def valid_phone(value: str) -> bool:
    return bool(re.fullmatch(r"(?:\+225)?\s?\d{10}", value.replace(" ", "")))


def verifier_code_tresor_pay(code: str) -> bool:
    # TODO: remplacer cette validation de format par l'API officielle de paiement.
    return bool(re.fullmatch(r"[A-Za-z0-9-]{6,50}", code))


def validate_upload(upload) -> tuple[bool, str]:
    if not upload or not upload.filename:
        return True, ""
    extension = Path(upload.filename).suffix.lower().lstrip(".")
    if extension not in MAGIC_BYTES:
        return False, "Format de fichier refusé. Utilisez PDF, JPG, JPEG ou PNG."
    upload.seek(0, 2)
    size = upload.tell()
    upload.seek(0)
    if size > 5 * 1024 * 1024:
        return False, "Chaque fichier doit peser au maximum 5 Mo."
    header = upload.read(16)
    upload.seek(0)
    if not any(header.startswith(value) for value in MAGIC_BYTES[extension]):
        return False, "Le contenu réel du fichier ne correspond pas à son extension."
    return True, ""


def validate_application(data: dict[str, str], files) -> dict[str, str]:
    errors: dict[str, str] = {}
    required = ("nom", "prenoms", "telephone", "sexe", "date_naissance", "annee_bac", "serie_bac", "numero_bac", "mention", "moyenne_bac", "choix_1_filiere", "tuteur1_nom")
    for field in required:
        if not data.get(field, "").strip():
            errors[field] = "Ce champ est obligatoire."
    if data.get("sexe") not in ("M", "F"):
        errors["sexe"] = "Sélection invalide."
    if data.get("nature_piece") and data["nature_piece"] not in NATURES_PIECE:
        errors["nature_piece"] = "Type de pièce invalide."
    if data.get("choix_1_filiere") not in FILIERES:
        errors["choix_1_filiere"] = "Filière invalide."
    if data.get("choix_2_filiere") and data["choix_2_filiere"] not in FILIERES:
        errors["choix_2_filiere"] = "Filière invalide."
    if data.get("choix_1_filiere") == data.get("choix_2_filiere") and data.get("choix_2_filiere"):
        errors["choix_2_filiere"] = "Les deux choix doivent être différents."
    if data.get("telephone") and not valid_phone(data["telephone"]):
        errors["telephone"] = "Numéro de téléphone invalide."
    if data.get("code_tresor_pay") and not verifier_code_tresor_pay(data["code_tresor_pay"]):
        errors["code_tresor_pay"] = "Code Trésor Pay invalide."
    for field in ("moyenne_bac", "note_math_bac", "note_physique_bac", "note_francais_bac", "note_anglais_bac"):
        if data.get(field):
            try:
                if not 0 <= float(data[field]) <= 20:
                    errors[field] = "La note doit être comprise entre 0 et 20."
            except ValueError:
                errors[field] = "Valeur numérique invalide."
    if data.get("annee_bac"):
        try:
            year = int(data["annee_bac"])
            if not datetime.now().year - 10 <= year <= datetime.now().year:
                errors["annee_bac"] = "Année de BAC invalide."
        except ValueError:
            errors["annee_bac"] = "Année invalide."
    for field in ("photo", "cni", "acte_naissance", "releve_bac"):
        if not files.get(field) or not files[field].filename:
            errors[field] = "Ce document est obligatoire à la soumission."
    for field, upload in files.items():
        valid, message = validate_upload(upload)
        if not valid:
            errors[field] = message
    return errors


@app.context_processor
def inject_config():
    return {
        "contact_email": app.config["CONTACT_EMAIL"],
        "contact_phone": app.config["CONTACT_PHONE"],
        "contact_secretariat": app.config.get("CONTACT_SECRETARIAT", ""),
        "contact_geo_address": app.config.get("CONTACT_GEO_ADDRESS", ""),
        "contact_postal_address": app.config.get("CONTACT_POSTAL_ADDRESS", ""),
        "contact_opening_hours": app.config.get("CONTACT_OPENING_HOURS", ""),
        "contact_website": app.config.get("CONTACT_WEBSITE", ""),
        "global_candidate": current_candidate(),
    }


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.route("/")
def home():
    candidate = current_candidate()
    if candidate and candidate["is_admin"]:
        return redirect(url_for("admin"))
    return redirect(url_for("candidature" if candidate else "connexion"))


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    candidate = current_candidate()
    if candidate and candidate["is_admin"]:
        return redirect(url_for("admin"))
    if candidate:
        return redirect(url_for("candidature"))
    next_url = safe_next(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip().lower()
        key = (request.remote_addr or "inconnu", identifiant)
        failures = [item for item in login_failures.get(key, []) if item > datetime.now(timezone.utc) - timedelta(minutes=15)]
        login_failures[key] = failures
        candidate = get_db().execute("SELECT * FROM candidats WHERE lower(email) = ? OR lower(numero_dossier) = ?", (identifiant, identifiant)).fetchone()
        if len(failures) >= 5:
            flash("Connexion temporairement bloquée. Réessayez plus tard.", "danger")
        elif candidate and check_password_hash(candidate["mot_de_passe"], request.form.get("password", "")):
            login_failures.pop(key, None)
            session.clear()
            session["candidate_id"] = candidate["id"]
            if candidate["is_admin"]:
                return redirect(url_for("admin"))
            return redirect(next_url or url_for("candidature"))
        else:
            failures.append(datetime.now(timezone.utc))
            login_failures[key] = failures
            flash("Identifiant ou mot de passe incorrect.", "danger")
    return render_template("connexion.html", next_url=next_url or "", google_enabled=bool(app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET")))


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if current_candidate():
        return redirect(url_for("candidature"))
    values = request.form.to_dict() if request.method == "POST" else {}
    if request.method == "POST":
        email = values.get("email", "").strip().lower()
        if not valid_email(email):
            flash("Adresse email invalide.", "danger")
        elif not valid_phone(values.get("telephone", "")):
            flash("Numéro de téléphone invalide.", "danger")
        elif not values.get("nom", "").strip() or not values.get("prenoms", "").strip():
            flash("Le nom et les prénoms sont obligatoires.", "danger")
        elif values.get("password", "") != values.get("password_confirmation", ""):
            flash("Les mots de passe ne correspondent pas.", "danger")
        elif len(values.get("password", "")) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
        else:
            try:
                cursor = get_db().execute("INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (dossier_number(), email, generate_password_hash(values["password"]), values["nom"].strip(), values["prenoms"].strip(), values["telephone"].strip(), now()))
                get_db().commit()
                candidate = get_db().execute("SELECT numero_dossier FROM candidats WHERE id = ?", (cursor.lastrowid,)).fetchone()
                flash(f"Compte créé. Votre numéro de dossier est {candidate['numero_dossier']}.", "success")
                try:
                    send_email(email, "Bienvenue à EMSP", f"Bonjour {values['prenoms'].strip()},\n\nVotre compte a été créé avec succès.\nNuméro de dossier : {candidate['numero_dossier']}\n\nVous pouvez maintenant compléter votre candidature.\n\nL'équipe EMSP")
                except Exception:
                    pass
                return redirect(url_for("connexion", identifiant=email))
            except sqlite3.IntegrityError:
                flash("Cette adresse email possède déjà un compte.", "danger")
    return render_template("inscription.html", values=values, google_enabled=bool(app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET")))


@app.post("/deconnexion")
@login_required
def deconnexion():
    session.clear()
    return redirect(url_for("connexion"))


@app.get("/login/google")
def login_google():
    if not app.config["GOOGLE_CLIENT_ID"] or not app.config["GOOGLE_CLIENT_SECRET"]:
        flash("La connexion Google n'est pas configurée. Vérifiez GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET dans le fichier .env.", "warning")
        return redirect(url_for("connexion"))
    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    response = redirect("https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(f"{key}={requests.utils.quote(str(value))}" for key, value in {
        "client_id": app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": app.config["GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }.items()))
    response.set_cookie("google_oauth_state", state, max_age=600, httponly=True, secure=os.environ.get("FLASK_DEBUG", "0") != "1", samesite="Lax")
    response.set_cookie("google_oauth_code_verifier", code_verifier, max_age=600, httponly=True, secure=os.environ.get("FLASK_DEBUG", "0") != "1", samesite="Lax")
    session["google_oauth_state"] = state
    session["google_oauth_code_verifier"] = code_verifier
    return response


@app.get("/login/google/authorized")
def login_google_authorized():
    error = request.args.get("error")
    if error:
        flash("Connexion Google annulée ou refusée.", "warning")
        return redirect(url_for("connexion"))
    state = request.args.get("state")
    cookie_state = request.cookies.get("google_oauth_state") or session.pop("google_oauth_state", None)
    if not state or not cookie_state or state != cookie_state:
        flash("Session de connexion invalide.", "danger")
        return redirect(url_for("connexion"))
    code = request.args.get("code")
    if not code:
        flash("Code d'autorisation manquant.", "danger")
        return redirect(url_for("connexion"))
    code_verifier = request.cookies.get("google_oauth_code_verifier", "") or session.pop("google_oauth_code_verifier", "")
    token_data = {
        "code": code,
        "client_id": app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": app.config["GOOGLE_REDIRECT_URI"],
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    if app.config.get("GOOGLE_CLIENT_SECRET"):
        token_data["client_secret"] = app.config["GOOGLE_CLIENT_SECRET"]
    try:
        token_response = requests.post("https://oauth2.googleapis.com/token", data=token_data, timeout=10)
    except requests.RequestException:
        google_logger.warning("Google injoignable lors de l'échange du code.")
        flash("Google est momentanément injoignable. Réessayez dans un instant.", "danger")
        return redirect(url_for("connexion"))
    google_logger.info("Token status=%s", token_response.status_code)
    if token_response.status_code != 200:
        try:
            payload = token_response.json()
        except ValueError:
            payload = {"raw": token_response.text}
        google_logger.warning("Échange de token échoué : %s", payload)
        error_description = payload.get("error_description") or payload.get("error") or payload.get("raw", "Échange de token échoué.")
        flash(f"Échange de token échoué : {error_description}", "danger")
        return redirect(url_for("connexion"))
    tokens = token_response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        flash("Token d'accès manquant.", "danger")
        return redirect(url_for("connexion"))
    try:
        user_response = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    except requests.RequestException:
        app.logger.warning("Google injoignable lors de la lecture du profil.")
        flash("Google est momentanément injoignable. Réessayez dans un instant.", "danger")
        return redirect(url_for("connexion"))
    if user_response.status_code != 200:
        flash("Récupération du profil échouée.", "danger")
        return redirect(url_for("connexion"))
    profile = user_response.json()
    email = profile.get("email", "").lower()
    if not email:
        flash("Profil Google incomplet.", "warning")
        return redirect(url_for("connexion"))
    if profile.get("verified_email") is not True:
        flash("Votre adresse Google n'est pas vérifiée. Utilisez un autre compte ou créez un compte avec e-mail.", "warning")
        return redirect(url_for("connexion"))
    db = get_db()
    candidate = db.execute("SELECT * FROM candidats WHERE lower(email) = ?", (email,)).fetchone()
    if candidate is None:
        try:
            cursor = db.execute("INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (dossier_number(), email, generate_password_hash(secrets.token_hex(16)), profile.get("family_name", ""), profile.get("given_name", ""), profile.get("phone_number", ""), now()))
            db.commit()
            candidate = db.execute("SELECT * FROM candidats WHERE id = ?", (cursor.lastrowid,)).fetchone()
            flash("Compte Google créé avec succès.", "success")
            try:
                numero_dossier, dossier_path = creer_dossier_utilisateur(email)
                db.execute("INSERT INTO dossiers_physiques (candidat_id, numero_dossier, chemin_dossier, cree_le) VALUES (?, ?, ?, ?)", (candidate["id"], numero_dossier, dossier_path, now()))
                db.commit()
                app.logger.info("Dossier utilisateur créé : %s -> %s", numero_dossier, dossier_path)
            except Exception as dossier_exception:
                app.logger.warning("Impossible de créer ou d'enregistrer le dossier physique pour %s : %s", email, dossier_exception)
                flash("Votre compte est créé, mais le dossier physique n'a pas pu être initialisé. L'équipe peut corriger cela plus tard.", "warning")
            try:
                send_email(email, "Bienvenue à EMSP", f"Bonjour {profile.get('given_name', '')},\n\nVotre compte Google a été lié avec succès.\nNuméro de dossier : {candidate['numero_dossier']}\n\nVous pouvez maintenant compléter votre candidature.\n\nL'équipe EMSP")
            except Exception:
                pass
        except sqlite3.IntegrityError:
            flash("Cette adresse email possède déjà un compte.", "danger")
            return redirect(url_for("connexion"))
    else:
        flash("Connexion Google réussie.", "success")
    session.clear()
    session["candidate_id"] = candidate["id"]
    return redirect(url_for("candidature"))


@app.route("/profil", methods=["GET", "POST"])
@login_required
def profil():
    candidate = current_candidate()
    values = {
        "nom": candidate["nom"],
        "prenoms": candidate["prenoms"],
        "telephone": candidate["telephone"],
        "email": candidate["email"],
    }
    if request.method == "POST":
        values.update({field: request.form.get(field, "").strip() for field in values})
        new_password = request.form.get("password", "")
        confirmation = request.form.get("password_confirmation", "")
        errors = []
        if not values["nom"] or not values["prenoms"]:
            errors.append("Le nom et les prénoms sont obligatoires.")
        if not valid_email(values["email"]):
            errors.append("L'adresse email est invalide.")
        if not valid_phone(values["telephone"]):
            errors.append("Le numéro de téléphone est invalide.")
        duplicate = get_db().execute("SELECT id FROM candidats WHERE email = ? AND id != ?", (values["email"].lower(), candidate["id"])).fetchone()
        if duplicate:
            errors.append("Cette adresse email est déjà utilisée.")
        if new_password and (len(new_password) < 8 or new_password != confirmation):
            errors.append("Le nouveau mot de passe doit contenir 8 caractères et ses confirmations doivent correspondre.")
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("profil.html", candidate=candidate, values=values)
        password_hash = generate_password_hash(new_password) if new_password else candidate["mot_de_passe"]
        get_db().execute("UPDATE candidats SET nom = ?, prenoms = ?, telephone = ?, email = ?, mot_de_passe = ? WHERE id = ?", (values["nom"], values["prenoms"], values["telephone"], values["email"].lower(), password_hash, candidate["id"]))
        get_db().commit()
        flash("Votre profil a été mis à jour.", "success")
        return redirect(url_for("profil"))
    return render_template("profil.html", candidate=candidate, values=values)


@app.route("/conditions")
def conditions():
    return render_template("conditions.html")


@app.get("/design-system")
def design_system():
    if not app.debug:
        abort(404)
    return render_template("design_system.html")


@app.route("/candidature", methods=["GET", "POST"])
@login_required
def candidature():
    candidate = current_candidate()
    db = get_db()
    current = db.execute("SELECT * FROM candidatures WHERE candidat_id = ?", (candidate["id"],)).fetchone()
    documents = db.execute("SELECT * FROM documents WHERE candidature_id = ?", (current["id"],)).fetchall() if current else []
    values = dict(current) if current else {}
    if request.method == "POST":
        if current and current["statut"] != "brouillon":
            flash("Ce dossier est verrouillé après sa soumission.", "warning")
            return redirect(url_for("candidature"))
        data = {field: request.form.get(field, "").strip() for field in ALLOWED_FIELDS}
        data["nom"] = data["nom"] or candidate["nom"]
        data["prenoms"] = data["prenoms"] or candidate["prenoms"]
        data["telephone"] = data["telephone"] or candidate["telephone"]
        action = request.form.get("action", "brouillon")
        errors = validate_application(data, request.files) if action == "soumettre" else {}
        if data.get("code_tresor_pay"):
            duplicate = db.execute("SELECT id FROM candidatures WHERE code_tresor_pay = ? AND candidat_id != ?", (data["code_tresor_pay"], candidate["id"])).fetchone()
            if duplicate:
                errors["code_tresor_pay"] = "Ce code Trésor Pay est déjà utilisé."
        if errors:
            for field, message in errors.items():
                flash(f"{field} : {message}", "danger")
            values.update(data)
            return render_template("candidature.html", candidate=candidate, c=values, documents=documents, errors=errors)
        status = "soumise" if action == "soumettre" else "brouillon"
        columns = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{column}=excluded.{column}" for column in data)
        db.execute(f"INSERT INTO candidatures (candidat_id, {columns}, statut, created_at, updated_at, submitted_at) VALUES (?, {placeholders}, ?, ?, ?, ?) ON CONFLICT(candidat_id) DO UPDATE SET {updates}, statut=excluded.statut, updated_at=excluded.updated_at, submitted_at=excluded.submitted_at", (candidate["id"], *data.values(), status, now(), now(), now() if status == "soumise" else None))
        db.commit()
        current = db.execute("SELECT * FROM candidatures WHERE candidat_id = ?", (candidate["id"],)).fetchone()
        for field in FILE_FIELDS:
            upload = request.files.get(field)
            if not upload or not upload.filename:
                continue
            valid, message = validate_upload(upload)
            if not valid:
                flash(message, "danger")
                continue
            extension = Path(upload.filename).suffix.lower()
            stored_name = secrets.token_hex(24) + extension
            candidate_dir = UPLOAD_DIR / str(candidate["id"])
            candidate_dir.mkdir(exist_ok=True)
            upload.save(candidate_dir / stored_name)
            db.execute("INSERT INTO documents (candidature_id, champ, nom_original, nom_stocke, mime, taille, created_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(candidature_id, champ) DO UPDATE SET nom_original=excluded.nom_original, nom_stocke=excluded.nom_stocke, mime=excluded.mime, taille=excluded.taille, created_at=excluded.created_at", (current["id"], field, upload.filename, stored_name, upload.mimetype, (candidate_dir / stored_name).stat().st_size, now()))
        db.commit()
        if status == "soumise":
            try:
                send_email(candidate["email"], "Candidature EMSP soumise", f"Bonjour {candidate['prenoms']},\n\nVotre candidature {candidate['numero_dossier']} a bien été soumise.\n\nVous recevrez une notification dès qu'une décision aura été prise.\n\nL'équipe EMSP")
            except Exception:
                pass
        flash("Brouillon enregistré." if status == "brouillon" else "Votre candidature a été soumise.", "success")
        return redirect(url_for("candidature"))
    convocation_state = "none" if not current else current["statut"]
    return render_template("candidature.html", candidate=candidate, c=values, documents=documents, errors={}, convocation_state=convocation_state)


@app.get("/documents/<int:document_id>")
@login_required
def document(document_id: int):
    row = get_db().execute("SELECT d.*, c.candidat_id FROM documents d JOIN candidatures c ON c.id = d.candidature_id WHERE d.id = ?", (document_id,)).fetchone()
    candidate = current_candidate()
    if row is None or (row["candidat_id"] != candidate["id"] and not candidate["is_admin"]):
        abort(404)
    return send_from_directory(UPLOAD_DIR / str(row["candidat_id"]), row["nom_stocke"], as_attachment=False)


@app.route("/dossiers-physiques")
@login_required
def dossiers_physiques():
    candidate = current_candidate()
    db = get_db()
    dossiers = db.execute("SELECT * FROM dossiers_physiques WHERE candidat_id = ? ORDER BY cree_le DESC", (candidate["id"],)).fetchall()
    return render_template("dossiers_physiques.html", dossiers=dossiers, candidate=candidate)


@app.route("/dossiers-physiques/<int:dossier_id>")
@login_required
def voir_dossier(dossier_id: int):
    candidate = current_candidate()
    db = get_db()
    dossier = db.execute("SELECT * FROM dossiers_physiques WHERE id = ? AND candidat_id = ?", (dossier_id, candidate["id"])).fetchone()
    if not dossier:
        flash("Dossier introuvable.", "danger")
        return redirect(url_for("dossiers_physiques"))
    try:
        fichiers = sorted(os.listdir(dossier["chemin_dossier"]))
    except Exception as e:
        flash(f"Impossible de lire le dossier: {e}", "danger")
        return redirect(url_for("dossiers_physiques"))
    return render_template("voir_dossier.html", dossier=dossier, fichiers=fichiers, candidate=candidate)


@app.post("/dossiers-physiques/<int:dossier_id>/upload")
@login_required
def upload_fichier(dossier_id: int):
    candidate = current_candidate()
    db = get_db()
    dossier = db.execute("SELECT * FROM dossiers_physiques WHERE id = ? AND candidat_id = ?", (dossier_id, candidate["id"])).fetchone()
    if not dossier:
        flash("Dossier introuvable.", "danger")
        return redirect(url_for("dossiers_physiques"))
    fichier = request.files.get("fichier")
    if not fichier or not fichier.filename:
        flash("Aucun fichier sélectionné.", "danger")
        return redirect(url_for("voir_dossier", dossier_id=dossier_id))
    try:
        chemin_fichier = os.path.join(dossier["chemin_dossier"], fichier.filename)
        fichier.save(chemin_fichier)
        flash(f"Fichier {fichier.filename} uploadé avec succès.", "success")
    except Exception as e:
        flash(f"Impossible d'uploader le fichier: {e}", "danger")
    return redirect(url_for("voir_dossier", dossier_id=dossier_id))

@app.route("/contacts", methods=["GET", "POST"])
def contacts():
    if request.method == "POST":
        form = request.form
        email = form.get("email", "").strip()
        message = form.get("message", "").strip()
        if not valid_email(email) or not message or len(message) > 5000:
            flash("Email invalide ou message trop long.", "danger")
        else:
            get_db().execute("INSERT INTO messages_contact (nom, email, telephone, objet, message, created_at) VALUES (?, ?, ?, ?, ?, ?)", (form.get("nom", "").strip(), email, form.get("telephone", "").strip(), form.get("objet", ""), message, now()))
            get_db().commit()
            flash("Votre message a bien été envoyé.", "success")
            return redirect(url_for("contacts"))
    return render_template("contacts.html")


@app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
def mot_de_passe_oublie():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        candidate = get_db().execute("SELECT * FROM candidats WHERE email = ?", (email,)).fetchone()
        if candidate:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            get_db().execute("INSERT INTO password_resets (candidat_id, token_hash, expires_at) VALUES (?, ?, ?)", (candidate["id"], token_hash, (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()))
            get_db().commit()
            reset_path = url_for("reinitialiser_mot_de_passe", token=token)
            base_url = app.config["PUBLIC_BASE_URL"] or request.url_root.rstrip("/")
            reset_url = f"{base_url}{reset_path}"
            try:
                if app.config["SMTP_HOST"]:
                    send_password_reset_email(email, reset_url)
                elif app.debug:
                    app.logger.warning("SMTP non configuré. Lien de test: %s", reset_url)
                else:
                    raise RuntimeError("SMTP_HOST n'est pas configuré.")
            except Exception as error:
                get_db().execute("DELETE FROM password_resets WHERE token_hash = ?", (token_hash,))
                get_db().commit()
                app.logger.error("Échec de l'envoi du lien de réinitialisation (%s).", type(error).__name__)
        flash("Si cette adresse existe, un lien de réinitialisation sera envoyé.", "info")
        return redirect(url_for("mot_de_passe_oublie"))
    return render_template("mot_de_passe_oublie.html")


@app.route("/reinitialiser-mot-de-passe/<token>", methods=["GET", "POST"])
def reinitialiser_mot_de_passe(token: str):
    reset = get_db().execute("SELECT * FROM password_resets WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?", (hashlib.sha256(token.encode()).hexdigest(), now())).fetchone()
    if reset is None:
        abort(400)
    if request.method == "POST":
        password = request.form.get("password", "")
        if len(password) < 8 or password != request.form.get("password_confirmation", ""):
            flash("Mot de passe invalide ou confirmation différente.", "danger")
        else:
            get_db().execute("UPDATE candidats SET mot_de_passe = ? WHERE id = ?", (generate_password_hash(password), reset["candidat_id"]))
            get_db().execute("UPDATE password_resets SET used_at = ? WHERE id = ?", (now(), reset["id"]))
            get_db().commit()
            flash("Mot de passe réinitialisé. Vous pouvez vous connecter.", "success")
            return redirect(url_for("connexion"))
    return render_template("reinitialiser_mot_de_passe.html")


@app.route("/admis")
def admis():
    published = get_db().execute("SELECT valeur FROM parametres WHERE cle = 'resultats_publies'").fetchone()["valeur"] == "1"
    result = None
    if published and current_candidate():
        result = get_db().execute("SELECT admis_concours, filiere_formation FROM candidatures WHERE candidat_id = ?", (current_candidate()["id"],)).fetchone()
    return render_template("admis.html", published=published, result=result)


@app.get("/admin")
@admin_required
def admin():
    db = get_db()
    total_candidatures = db.execute("SELECT COUNT(*) FROM candidatures").fetchone()[0]
    brouillons = db.execute("SELECT COUNT(*) FROM candidatures WHERE statut='brouillon'").fetchone()[0]
    soumises = db.execute("SELECT COUNT(*) FROM candidatures WHERE statut='soumise'").fetchone()[0]
    validees = db.execute("SELECT COUNT(*) FROM candidatures WHERE statut='validee'").fetchone()[0]
    rejetees = db.execute("SELECT COUNT(*) FROM candidatures WHERE statut='rejetee'").fetchone()[0]
    total_dossiers_physiques = db.execute("SELECT COUNT(*) FROM dossiers_physiques").fetchone()[0]
    return render_template("admin_home.html", candidate=current_candidate(), total_candidatures=total_candidatures, brouillons=brouillons, soumises=soumises, validees=validees, rejetees=rejetees, total_dossiers_physiques=total_dossiers_physiques)


@app.get("/admin/candidatures")
@admin_required
def admin_candidatures():
    status = request.args.get("statut", "")
    filiere = request.args.get("filiere", "")
    search = request.args.get("recherche", "").strip()
    query = "SELECT ca.*, c.numero_dossier, c.nom AS candidat_nom, c.prenoms AS candidat_prenoms FROM candidatures ca JOIN candidats c ON c.id = ca.candidat_id WHERE 1=1"
    params = []
    if status:
        query += " AND ca.statut = ?"; params.append(status)
    if filiere:
        query += " AND ca.choix_1_filiere = ?"; params.append(filiere)
    if search:
        query += " AND (c.nom LIKE ? OR c.prenoms LIKE ? OR c.numero_dossier LIKE ?)"; params.extend([f"%{search}%"] * 3)
    rows = get_db().execute(query + " ORDER BY ca.updated_at DESC", params).fetchall()
    return render_template("admin.html", candidatures=rows, filieres=FILIERES, filters={"statut": status, "filiere": filiere, "recherche": search}, candidate=current_candidate())


@app.get("/admin/candidature/<int:candidature_id>")
@admin_required
def admin_candidature(candidature_id: int):
    row = get_db().execute("SELECT ca.*, c.numero_dossier, c.email FROM candidatures ca JOIN candidats c ON c.id = ca.candidat_id WHERE ca.id = ?", (candidature_id,)).fetchone()
    if row is None:
        abort(404)
    documents = get_db().execute("SELECT * FROM documents WHERE candidature_id = ?", (candidature_id,)).fetchall()
    return render_template("admin_candidature.html", candidature=row, documents=documents, filieres=FILIERES)


@app.post("/admin/candidature/<int:candidature_id>")
@admin_required
def admin_update(candidature_id: int):
    action = request.form.get("action")
    status = "validee" if action == "valider" else "rejetee" if action == "rejeter" else None
    if status:
        get_db().execute("UPDATE candidatures SET statut = ?, dossier_valide = ?, date_compo = ?, centre_compo = ?, updated_at = ? WHERE id = ?", (status, int(status == "validee"), request.form.get("date_compo") or None, request.form.get("centre_compo") or None, now(), candidature_id))
    get_db().execute("UPDATE candidatures SET note_francais_compo=?, note_math_compo=?, note_anglais_compo=?, note_psycho_compo=?, admis_concours=?, filiere_formation=?, updated_at=? WHERE id=?", (request.form.get("note_francais_compo") or None, request.form.get("note_math_compo") or None, request.form.get("note_anglais_compo") or None, request.form.get("note_psycho_compo") or None, int(request.form.get("admis_concours") == "1"), request.form.get("filiere_formation") or None, now(), candidature_id))
    get_db().commit()
    row = get_db().execute("SELECT c.email, c.nom, c.prenoms, ca.numero_dossier, ca.statut FROM candidatures ca JOIN candidats c ON c.id = ca.candidat_id WHERE ca.id = ?", (candidature_id,)).fetchone()
    if row and status:
        try:
            subject = "Dossier validé" if status == "validee" else "Dossier non retenu"
            body = f"Bonjour {row['prenoms']},\n\nVotre dossier {row['numero_dossier']} a été marqué comme {'retenu' if status == 'validee' else 'non retenu'}.\n\nL'équipe EMSP"
            send_email(row["email"], subject, body)
        except Exception:
            pass
    flash("Dossier administré.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/resultats")
@admin_required
def toggle_results():
    current = get_db().execute("SELECT valeur FROM parametres WHERE cle = 'resultats_publies'").fetchone()["valeur"]
    get_db().execute("UPDATE parametres SET valeur = ? WHERE cle = 'resultats_publies'", ("0" if current == "1" else "1",))
    get_db().commit()
    if current == "0":
        try:
            for row in get_db().execute("SELECT c.email, c.prenoms, ca.numero_dossier, ca.admis_concours, ca.filiere_formation FROM candidatures ca JOIN candidats c ON c.id = ca.candidat_id WHERE ca.statut='validee'").fetchall():
                send_email(row["email"], "Résultats EMSP publiés", f"Bonjour {row['prenoms']},\n\nLes résultats sont maintenant disponibles dans votre espace candidat.\nDossier : {row['numero_dossier']}\n\nL'équipe EMSP")
        except Exception:
            pass
    flash("Publication des résultats mise à jour.", "success")
    return redirect(url_for("admin"))


@app.get("/admin/export.csv")
@admin_required
def export_csv():
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["numero_dossier", "nom", "prenoms", "statut", "filiere"])
    for row in get_db().execute("SELECT c.numero_dossier, c.nom, c.prenoms, ca.statut, ca.choix_1_filiere FROM candidatures ca JOIN candidats c ON c.id=ca.candidat_id"):
        writer.writerow(row)
    return app.response_class(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=candidatures.csv"})


@app.get("/admin/dossiers-physiques")
@admin_required
def admin_dossiers_physiques():
    db = get_db()
    dossiers = db.execute("SELECT dp.*, c.nom AS candidat_nom, c.prenoms AS candidat_prenoms, c.email AS candidat_email FROM dossiers_physiques dp JOIN candidats c ON c.id = dp.candidat_id ORDER BY dp.cree_le DESC").fetchall()
    return render_template("admin_dossiers_physiques.html", dossiers=dossiers)


@app.get("/admin/dossiers-physiques/<int:dossier_id>")
@admin_required
def admin_voir_dossier(dossier_id: int):
    db = get_db()
    dossier = db.execute("SELECT dp.*, c.nom AS candidat_nom, c.prenoms AS candidat_prenoms, c.email AS candidat_email FROM dossiers_physiques dp JOIN candidats c ON c.id = dp.candidat_id WHERE dp.id = ?", (dossier_id,)).fetchone()
    if not dossier:
        abort(404)
    try:
        fichiers = sorted(os.listdir(dossier["chemin_dossier"]))
    except Exception as e:
        flash(f"Impossible de lire le dossier: {e}", "danger")
        return redirect(url_for("admin_dossiers_physiques"))
    return render_template("admin_voir_dossier.html", dossier=dossier, fichiers=fichiers)


@app.cli.command("create-admin")
@click.option("--email", prompt="Email administrateur")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(email: str, password: str):
    """Crée ou élève un compte administrateur sans compte par défaut."""
    if not valid_email(email) or len(password) < 8:
        raise click.ClickException("Email invalide ou mot de passe trop court.")
    candidate = get_db().execute("SELECT id FROM candidats WHERE email = ?", (email.lower(),)).fetchone()
    if candidate:
        get_db().execute("UPDATE candidats SET is_admin = 1, mot_de_passe = ? WHERE id = ?", (generate_password_hash(password), candidate["id"]))
    else:
        get_db().execute("INSERT INTO candidats (numero_dossier, email, mot_de_passe, nom, prenoms, telephone, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)", (dossier_number(), email.lower(), generate_password_hash(password), "Administrateur", "EMSP", "0000000000", now()))
    get_db().commit()
    click.echo("Compte administrateur prêt.")


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Accès refusé."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Page introuvable."), 404


@app.errorhandler(413)
def too_large(_error):
    return render_template("error.html", code=413, message="Fichier trop volumineux."), 413


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, message="Une erreur interne est survenue."), 500


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
