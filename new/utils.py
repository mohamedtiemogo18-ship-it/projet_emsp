import os
import time
import random


def creer_dossier_utilisateur(email_google):
    email_clean = email_google.replace("@", "_").replace(".", "_")
    timestamp = int(time.time())
    rand_id = random.randint(1000, 9999)
    numero_dossier = f"DOSSIER-{email_clean}-{timestamp}-{rand_id}"

    base_dir = os.path.join(os.getcwd(), "dossiers_utilisateurs")
    user_folder_path = os.path.join(base_dir, numero_dossier)

    os.makedirs(user_folder_path, exist_ok=True)

    info_file_path = os.path.join(user_folder_path, "infos_session.txt")
    with open(info_file_path, "w", encoding="utf-8") as f:
        f.write(f"Numéro de dossier : {numero_dossier}\n")
        f.write(f"Email Google associé : {email_google}\n")
        f.write(f"Date de création : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    return numero_dossier, user_folder_path
