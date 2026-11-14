"""logwatch : analyse d'un log nginx (santé du site, pics de 5xx, alerte webhook).

Squelette de l'étape 1 : les fonctions sont déclarées, l'implémentation
arrive aux étapes 3 à 7 (voir docs/conception.md).
"""

import sys

# Codes de sortie
EXIT_OK = 0          # aucun pic
EXIT_PEAK = 1        # au moins une minute en pic
EXIT_ERROR = 2       # fichier absent/illisible, aucune ligne valide, config invalide, --alert sans URL

DEFAULT_CONFIG_PATH = "logwatch.json"   # utilisé seulement s'il existe

DEFAULT_CONFIG = {
    "threshold_5xx": 0.05,
    "min_requests": 50,
    "top_n": 10,
    "exclude_paths": ["/health", "/metrics"],
    "webhook_timeout_s": 5,
}


def parse_args(argv):
    """CLI argparse (étape 5 – personne B)."""
    raise NotImplementedError


def load_config(path):
    """Charge et valide la config JSON (étape 5 – personne B)."""
    raise NotImplementedError


def parse_line(line):
    """Regex nginx combined + $request_time -> dict ou None (étape 3 – personne A)."""
    raise NotImplementedError


def read_log(path, exclude_paths):
    """Lecture ligne à ligne, comptage des lignes invalides (étape 3 – personne A)."""
    raise NotImplementedError


def compute_stats(entries, config):
    """Volume, taux 4xx/5xx, tops, latences, agrégation par minute, pics (étape 4 – personne A)."""
    raise NotImplementedError


def build_report(stats, config):
    """Rapport JSON ou texte (étape 6 – personne B)."""
    raise NotImplementedError


def send_alert(report, timeout_s):
    """POST vers LOGWATCH_WEBHOOK_URL (étape 7 – personne B)."""
    raise NotImplementedError


def main(argv=None):
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
