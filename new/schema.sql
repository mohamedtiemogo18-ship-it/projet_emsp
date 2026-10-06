PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candidats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_dossier TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    mot_de_passe TEXT NOT NULL,
    nom TEXT NOT NULL,
    prenoms TEXT NOT NULL,
    telephone TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidat_id INTEGER NOT NULL UNIQUE REFERENCES candidats(id) ON DELETE CASCADE,
    code_tresor_pay TEXT UNIQUE,
    nom TEXT NOT NULL DEFAULT '', prenoms TEXT NOT NULL DEFAULT '', sexe TEXT,
    date_naissance TEXT, lieu_naissance TEXT, nationalite TEXT DEFAULT 'Ivoirienne',
    telephone TEXT, nature_piece TEXT, numero_piece TEXT, commune TEXT, ville TEXT, adresse TEXT,
    annee_bac INTEGER, serie_bac TEXT, numero_bac TEXT, numero_table TEXT, mention TEXT,
    moyenne_bac REAL, note_math_bac REAL, note_physique_bac REAL, note_francais_bac REAL, note_anglais_bac REAL,
    choix_1_filiere TEXT, choix_2_filiere TEXT,
    tuteur1_nom TEXT, tuteur1_contact TEXT, tuteur1_lien TEXT, tuteur1_residence TEXT,
    tuteur2_nom TEXT, tuteur2_contact TEXT, tuteur2_lien TEXT, tuteur2_residence TEXT,
    dossier_valide INTEGER NOT NULL DEFAULT 0 CHECK (dossier_valide IN (0, 1)),
    date_compo TEXT, centre_compo TEXT, note_francais_compo REAL, note_math_compo REAL,
    note_anglais_compo REAL, note_psycho_compo REAL,
    admis_concours INTEGER NOT NULL DEFAULT 0 CHECK (admis_concours IN (0, 1)), filiere_formation TEXT,
    statut TEXT NOT NULL DEFAULT 'brouillon' CHECK (statut IN ('brouillon', 'soumise', 'validee', 'rejetee')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, submitted_at TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidature_id INTEGER NOT NULL REFERENCES candidatures(id) ON DELETE CASCADE,
    champ TEXT NOT NULL, nom_original TEXT NOT NULL, nom_stocke TEXT NOT NULL,
    mime TEXT NOT NULL, taille INTEGER NOT NULL, created_at TEXT NOT NULL,
    UNIQUE (candidature_id, champ)
);

CREATE TABLE IF NOT EXISTS messages_contact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL, email TEXT NOT NULL, telephone TEXT, objet TEXT NOT NULL,
    message TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidat_id INTEGER NOT NULL REFERENCES candidats(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);

CREATE TABLE IF NOT EXISTS parametres (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
INSERT OR IGNORE INTO parametres (cle, valeur) VALUES ('resultats_publies', '0');

CREATE TABLE IF NOT EXISTS dossiers_physiques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidat_id INTEGER NOT NULL REFERENCES candidats(id) ON DELETE CASCADE,
    numero_dossier TEXT NOT NULL,
    chemin_dossier TEXT NOT NULL,
    cree_le TEXT NOT NULL
);
