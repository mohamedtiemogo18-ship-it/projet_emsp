# Audit UX EMSP

## Traité

- Feuilles CSS indépendantes : `tokens.css`, `base.css`, `components.css`, `layout.css` et un fichier par page.
- Identité : palette marine et jaune, polices Bricolage Grotesque et Instrument Sans, logo SVG remplaçable.
- Navigation : états actifs harmonisés (soulignement jaune), menu mobile conservé.
- Progression du dossier : anneau et repère dans la barre latérale, étapes cochées quand les champs obligatoires sont remplis, indicateur d'enregistrement fidèle à l'état réel du brouillon.
- Accessibilité : focus visible, contrastes corrigés (texte jaune sur blanc retiré, étapes jaunes avec texte marine), zones tactiles de 44 px, `prefers-reduced-motion` respecté.
- Dépendances allégées : AOS et Font Awesome retirés, une seule bibliothèque d'icônes.
- Thème sombre : variables de statut redéfinies pour les nouveaux composants.

## Reste à faire

- Factoriser `candidature.html` (plus de 2 000 lignes) en partiels Jinja.
- Retirer les anciennes feuilles inutilisées (`connexion.css`, `contacts.css`, `conditions.css`) après vérification.
- Vérifier le rendu dans les navigateurs cibles et sur de vrais mobiles.
