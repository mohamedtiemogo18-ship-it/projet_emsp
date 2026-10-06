# EMSP

Application Flask de candidature EMSP avec SQLite, authentification, dépôt de documents et espace d'administration.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Renseignez une valeur aléatoire pour `EMSP_SECRET_KEY` dans `.env`.

### Envoi des liens de réinitialisation avec Gmail

Dans les paramètres de sécurité du compte Google, activez la validation en deux étapes, puis créez un mot de passe d'application. Dans votre fichier `.env` local, renseignez `SMTP_USERNAME` avec l'adresse Gmail et `SMTP_PASSWORD` avec ce mot de passe d'application. `SMTP_SENDER` peut être cette même adresse (le code utilise `SMTP_USERNAME` s'il est laissé vide). L'exemple utilise `smtp.gmail.com`, le port 587 et STARTTLS. N'utilisez ni le mot de passe normal du compte Google ni `GOOGLE_CLIENT_SECRET` comme mot de passe SMTP, et ne partagez jamais ces secrets.

`PUBLIC_BASE_URL` doit correspondre à l'adresse utilisée pour ouvrir le site. La valeur d'exemple `http://127.0.0.1:5000` convient au développement local ; en production, remplacez-la par le domaine public en HTTPS. Redémarrez Flask après avoir modifié `.env`.

## Lancement

```powershell
flask --app app run --debug
```

Application : http://127.0.0.1:5000

## Administration

Aucun administrateur n'est créé par défaut. Utilisez la commande prévue par votre environnement ou mettez `is_admin = 1` sur un compte créé dans SQLite après vérification de son identité.

Les fichiers des candidats sont stockés dans `private_uploads/` et la base dans `instance/`, tous deux exclus du dépôt.
