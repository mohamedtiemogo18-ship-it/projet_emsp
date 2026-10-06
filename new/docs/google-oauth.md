# Connexion Google (OAuth 2.0 avec PKCE)

## Variables du fichier `.env`

| Variable | Rôle |
|---|---|
| `GOOGLE_CLIENT_ID` | Identifiant client créé dans la console Google Cloud |
| `GOOGLE_CLIENT_SECRET` | Secret du client (requis pour les applications Web) |
| `GOOGLE_REDIRECT_URI` | Adresse de retour, exactement `https://VOTRE-SITE/login/google/authorized` |
| `PUBLIC_BASE_URL` | Adresse publique du site. Si `GOOGLE_REDIRECT_URI` est vide, l'adresse de retour en est déduite |

Les boutons « Continuer avec Google » (connexion et inscription) n'apparaissent que si l'identifiant **et** le secret sont renseignés.

## Configuration dans Google Cloud

### 1. Créer un client OAuth 2.0

1. Ouvrir https://console.cloud.google.com
2. Sélectionner votre projet
3. Menu gauche : **API et services** > **Identifiants**
4. Cliquer sur **Créer des identifiants** > **ID client OAuth**
5. Type d'application : **Application Web**
6. Nom : `EMSP`
7. Dans **URI de redirection autorisés**, ajouter :
   - `http://localhost:5000/login/google/authorized` (développement local)
   - `https://VOTRE-SITE/login/google/authorized` (production, HTTPS obligatoire)
8. Cliquer sur **Créer**

### 2. Récupérer le Client ID et le Client secret

1. Toujours dans **API et services** > **Identifiants**
2. Cliquer sur le client OAuth 2.0 que vous venez de créer
3. Vous voyez :
   - **ID client** : copier cette valeur
   - **Secret client** : cliquer sur **Afficher** pour voir le secret, puis copier
4. Si vous ne voyez pas le secret, cliquer sur **Réinitialiser le secret**

### 3. Mettre à jour `.env`

```env
GOOGLE_CLIENT_ID=1069114930323-fdmpcnsfmushbhbsteakubl0g544fmim.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=ton-vrai-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/login/google/authorized
PUBLIC_BASE_URL=http://127.0.0.1:5000
```

### 4. Redémarrer l'application

```powershell
flask --app app run --debug
```

## Où trouver le Client ID et le Secret pas à pas

**Étape 1** : Aller dans Google Cloud Console
- URL : https://console.cloud.google.com
- Menu hamburger (☰) en haut à gauche

**Étape 2** : Navigation vers Identifiants
- Cliquer sur **API et services**
- Cliquer sur **Identifiants** (`Credentials`)

**Étape 3** : Voir le détail du client
- Dans la liste des identifiants, cliquer sur le nom du client OAuth 2.0
- Vous voyez une page avec :
  - **ID client** (en haut)
  - **Secret client** (plus bas)

**Étape 4** : Afficher le secret
- Cliquer sur le bouton **Afficher** à côté de "Secret client"
- Le secret apparaît en clair
- Le copier

**Si le secret n'apparaît pas**
- Cliquer sur **Réinitialiser le secret**
- Confirmer
- Copier le nouveau secret généré

**Attention** : le Secret Manager est une autre fonctionnalité (pour les clés API backend). Pour OAuth 2.0 web, restez dans **API et services** > **Identifiants**.

## Comportement

- Le parcours demande les droits `openid email profile`.
- Un jeton `state` protège le retour contre les requêtes forgées.
- Le protocole PKCE remplace le secret client pour l'échange du code.
- Le compte n'est accepté que si Google indique que l'adresse e-mail est **vérifiée** (`verified_email`).
- Si l'e-mail existe déjà, la personne est connectée à ce compte. Sinon, un compte candidat et son dossier physique sont créés.
- Si Google est injoignable, un message invite à réessayer au lieu d'afficher une erreur serveur.

## Dépannage

| Message de Google ou de l'application | Cause probable |
|---|---|
| `redirect_uri_mismatch` | L'adresse de `GOOGLE_REDIRECT_URI` n'est pas identique à celle déclarée dans Google Cloud (schéma, domaine, port, barre finale) |
| `access_denied` pour certains comptes | Application encore en mode « Test » : ajouter ces comptes comme testeurs ou publier l'application |
| « La connexion Google n'est pas configurée » | `GOOGLE_CLIENT_ID` vide |
| « Échange de token échoué » | Client ID erroné, ou adresse de retour différente entre la demande et l'échange |
| « Votre adresse Google n'est pas vérifiée » | Compte Google dont l'e-mail n'est pas confirmé |
