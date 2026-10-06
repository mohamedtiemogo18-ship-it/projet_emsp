# Système de design EMSP

## Direction

Portail institutionnel rassurant : bleu marine pour la confiance, bleu d'action pour les décisions, jaune uniquement comme accent (repères, progression, étapes terminées). Un seul moment animé par page, jamais d'animation sans raison. Les champs et actions gardent une taille confortable sur mobile.

## Couleurs (source : `static/css/tokens.css`)

| Rôle | Variable | Valeur |
|---|---|---|
| Fond de marque, panneaux | `--brand-900` | `#172335` |
| Liens, icônes | `--brand-700` | `#315EAA` |
| Accent (jamais en texte sur blanc) | `--accent-500` | `#F2BF2F` |
| Action | `--action` | `#315FCC` |
| Succès / erreur / alerte | `--success-600` / `--danger-600` / `--warning-700` | `#157347` / `#B42318` / `#B45309` |

Le jaune sert de fond, de trait ou d'icône sur fond sombre. Sur fond blanc, le texte utilise `--brand-700` ou `--brand-900`.

## Typographie

- Titres : Bricolage Grotesque (`--font-display`).
- Texte : Instrument Sans (`--font`), 16 px minimum, interligne 1,5.
- Pas de texte tout en majuscules ni d'étiquette décorative au-dessus des titres.

## Mouvement

- Courbe commune : `--ease`. Durées de 0,25 s (interactions) à 0,9 s (entrée de page).
- Les animations qui répondent à une action (ouvrir, valider, choisir un fichier) sont toujours autorisées.
- `prefers-reduced-motion` désactive toutes les animations.

## Règles

- Échelle d'espacement 4 / 8 px et trois rayons (`--radius-sm`, `--radius-md`, `--radius-lg`).
- Focus visible par anneau de 3 px.
- Les statuts affichent toujours une icône ou un libellé, jamais la couleur seule.
- Bibliothèque d'icônes unique : Bootstrap Icons.
- Un document attendu est en bordure pointillée, un document reçu en bordure pleine verte.
- Thème sombre : toute nouvelle couleur de texte ou de fond passe par une variable redéfinie dans `theme.css`.
