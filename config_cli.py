# Fichier mis à jour
# Prérequis : Avoir des fichiers de logs dans le dossier /data & avoir le fichier logwatch.json
import argparse
import json
import logging
from pathlib import Path


# CONFIGURATION PAR DEFAUT
DEFAULT_CONFIG_PATH = "logwatch.json"

DEFAULT_CONFIG = {
    "threshold_5xx": 0.05,
    "min_requests": 50,
    "top_n": 10,
    "exclude_paths": ["/health", "/metrics"],
    "webhook_timeout_s": 5
}


# VALIDATION DES ARGUMENTS CLI
def positive_int(value):
    #Vérifie qu'un argument entier est strictement positif.
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Une valeur entière est attendue.")

    if number <= 0:
        raise argparse.ArgumentTypeError("La valeur doit être supérieure à 0.")

    return number


def valid_threshold(value):
    #Vérifie que le seuil est compris entre 0 et 1.
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Un nombre est attendu.")

    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("Le seuil doit être compris entre 0 et 1.")

    return number


# 1. GESTION DE LA CLI
def parse_args(argv=None):
    # Récupère et valide les arguments de la ligne de commande.

    parser = argparse.ArgumentParser(
        description="Logwatch : analyseur de logs nginx et détecteur d'incidents."
    )

    # Fichier de logs obligatoire
    parser.add_argument("file", help="Chemin vers le fichier de logs à analyser.")

    # Configuration JSON
    parser.add_argument("--config", help="Chemin vers le fichier de configuration JSON.")

    # Paramètres d'analyse
    parser.add_argument("--threshold", type=valid_threshold, help="Seuil de détection des erreurs 5xx (entre 0 et 1).")

    parser.add_argument("--top", type=positive_int, help="Nombre d'IP et de routes à afficher.")

    # Format du rapport
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Format du rapport (json ou text).")

    parser.add_argument("--output", help="Chemin du fichier dans lequel enregistrer le rapport.")

    # Options supplémentaires
    parser.add_argument("--alert", action="store_true", help="Autorise l'envoi d'une alerte webhook en cas de pic.")

    parser.add_argument("--verbose", action="store_true", help="Active les messages de journalisation DEBUG.")

    return parser.parse_args(argv)



# 2. CHARGEMENT ET VALIDATION DE LA CONFIGURATION
def validate_config(config):
    #Vérifie les types et les valeurs de la configuration JSON.

    if not isinstance(config, dict):
        raise ValueError("La configuration doit être un objet JSON.")

    expected_keys = set(DEFAULT_CONFIG.keys())
    received_keys = set(config.keys())

    # Vérifier les clés inconnues
    unknown_keys = received_keys - expected_keys

    if unknown_keys:
        raise ValueError(f"Clés de configuration inconnues : {unknown_keys}")

    # threshold_5xx
    threshold = config["threshold_5xx"]

    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("threshold_5xx doit être un nombre.")

    if not 0 <= threshold <= 1:
        raise ValueError("threshold_5xx doit être compris entre 0 et 1.")

    # min_requests
    min_requests = config["min_requests"]

    if type(min_requests) is not int or min_requests <= 0:
        raise ValueError("min_requests doit être un entier positif.")

    # top_n
    top_n = config["top_n"]

    if type(top_n) is not int or top_n <= 0:
        raise ValueError("top_n doit être un entier positif.")

    # exclude_paths
    exclude_paths = config["exclude_paths"]

    if not isinstance(exclude_paths, list):
        raise ValueError("exclude_paths doit être une liste.")

    if not all(isinstance(path, str) and path for path in exclude_paths):
        raise ValueError("Chaque élément de exclude_paths doit être une chaîne non vide.")

    # webhook_timeout_s
    timeout = config["webhook_timeout_s"]

    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("webhook_timeout_s doit être un nombre.")

    if timeout <= 0:
        raise ValueError("webhook_timeout_s doit être supérieur à 0.")

    return config


def load_config(path=None):
    #Charge le JSON, complète les valeurs par défaut et valide la configuration.

    config = DEFAULT_CONFIG.copy()

    # Si aucun chemin n'est fourni, chercher logwatch.json
    if path is None:
        path = Path(DEFAULT_CONFIG_PATH)
        if not path.exists():
            return config
    else:
        path = Path(path)

    # Ouvrir et lire le fichier JSON
    try:
        with path.open("r", encoding="utf-8") as file:
            user_config = json.load(file)

    except OSError as error:
        raise ValueError(f"Impossible de lire la configuration : {error}")

    except json.JSONDecodeError as error:
        raise ValueError(f"Le fichier JSON est invalide : {error}")

    # Vérifier que la racine du JSON est un dictionnaire
    if not isinstance(user_config, dict):
        raise ValueError("Le fichier de configuration doit contenir un objet JSON.")

    # Remplacer les valeurs par défaut par celles du fichier
    config.update(user_config)

    # Vérifier la configuration complète
    validate_config(config)

    return config


# 3. PRIORITE DES PARAMETRES
def merge_config(config, args):
    #Applique les arguments CLI à la configuration JSON.

    # On crée une copie pour ne pas modifier le dictionnaire initial
    config = config.copy()

    # Le CLI est prioritaire sur le JSON
    if args.threshold is not None:
        config["threshold_5xx"] = args.threshold

    if args.top is not None:
        config["top_n"] = args.top

    return config


# 4. CONFIGURATION DU LOGGING
def setup_logging(verbose=False):
    #Configure le niveau de journalisation.

    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True
    )



# TEST RAPIDE DU MODULE
if __name__ == "__main__":
    args = parse_args()

    try:
        config = load_config(args.config)
        config = merge_config(config, args)

    except ValueError as error:
        print(f"Erreur de configuration : {error}")
        raise SystemExit(2)

    setup_logging(args.verbose)

    print("Arguments :")
    print(json.dumps(vars(args), indent=4, ensure_ascii=False))

    print("\nConfiguration :")
    print(json.dumps(config, indent=4, ensure_ascii=False))
