# EMSP

Application Flask de candidature EMSP avec SQLite en développement, Supabase PostgreSQL en production, authentification, dépôt de documents et espace d'administration.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Renseignez une valeur aléatoire pour `EMSP_SECRET_KEY` dans `.env`.

### Base de données Supabase sur Vercel

Pour conserver les comptes et candidatures en ligne, créez un projet Supabase et ajoutez sa chaîne de connexion PostgreSQL comme variable Vercel `DATABASE_URL`. Utilisez la chaîne de connexion du pooler Supabase (recommandée pour les fonctions serverless) et gardez son mot de passe privé. Au démarrage, l'application crée les tables nécessaires dans le schéma `public`. Sans `DATABASE_URL`, elle utilise SQLite localement ; le SQLite dans `/tmp` sur Vercel est temporaire et ne doit pas contenir les données de production.

Pour le développement local avec la base Supabase, ajoutez également `DATABASE_URL` à `.env`. Sinon, l'application continue d'utiliser SQLite dans `instance/`.

### Envoi des liens de réinitialisation avec Gmail

Dans les paramètres de sécurité du compte Google, activez la validation en deux étapes, puis créez un mot de passe d'application. Dans votre fichier `.env` local, renseignez `SMTP_USERNAME` avec l'adresse Gmail et `SMTP_PASSWORD` avec ce mot de passe d'application. `SMTP_SENDER` peut être cette même adresse (le code utilise `SMTP_USERNAME` s'il est laissé vide). L'exemple utilise `smtp.gmail.com`, le port 587 et STARTTLS. N'utilisez ni le mot de passe normal du compte Google ni `GOOGLE_CLIENT_SECRET` comme mot de passe SMTP, et ne partagez jamais ces secrets.

`PUBLIC_BASE_URL` doit correspondre à l'adresse utilisée pour ouvrir le site. La valeur d'exemple `http://127.0.0.1:5000` convient au développement local ; en production, remplacez-la par le domaine public en HTTPS. Redémarrez Flask après avoir modifié `.env`.

## Lancement

```powershell
flask --app app run --debug
```

Application : http://127.0.0.1:5000

## Administration

Aucun administrateur n'est créé par défaut. Après avoir configuré `DATABASE_URL` dans `.env`, créez ou promouvez le compte administrateur dans la base Supabase avec :

```powershell
flask --app app create-admin --email admin@exemple.org
```

La commande demande un mot de passe et l'enregistre sous forme hachée. Vérifiez l'identité de l'adresse avant de lui attribuer le rôle administrateur. Les fichiers téléversés restent dans le système de fichiers local ; sur Vercel, `/tmp` est temporaire. Utilisez un stockage objet persistant avant d'y conserver des documents de production.

En développement local avec SQLite, les fichiers des candidats sont stockés dans `private_uploads/` et la base dans `instance/`, tous deux exclus du dépôt.
