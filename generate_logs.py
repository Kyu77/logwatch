"""generate_logs.py : fabrique de faux logs nginx pour tester logwatch.

Lancement :  python3 generate_logs.py
Produit deux fichiers :
  - data/incident.log : un pic d'erreurs 5xx à la minute PEAK_MINUTE
  - data/calme.log    : aucun pic

Aucune donnée réelle : les IP viennent des plages réservées à la documentation
(RFC 5737) et le site est en .example. Même graine = même fichier, à chaque fois.
"""

import random
import sys
from pathlib import Path

# --- Réglages : tout se modifie ici ------------------------------------------
DATA_DIR = Path("data")  # chemin relatif : lancer le script depuis la racine du dépôt
SEED = 42                # graine : même graine = mêmes tirages = même fichier
START_HOUR = 1           # le log commence à 01:30...
START_MINUTE = 30
DURATION = 60            # ... et couvre 60 minutes
LINES_PER_MINUTE = 166   # bien plus que min_requests (50) : chaque minute est analysable
INVALID_EVERY = 500      # une ligne abîmée toutes les 500 lignes valides
PEAK_MINUTE = "02:07"    # minute du pic dans incident.log
DAY = "20/Nov/2026"      # écrit à la main : toujours "Nov", quelle que soit la langue du système
TIMEZONE = "+0100"

# Une route plus fréquente est simplement répétée dans la liste.
ROUTES = [
    "/", "/",
    "/produits", "/produits", "/produits",
    "/api/orders", "/api/orders", "/api/orders",
    "/api/payment",
    "/panier",
    "/static/app.js",
    "/health",       # à exclure par logwatch (exclude_paths)
    "/metrics",      # idem
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1.15",
    "curl/8.5.0",
]

REFERERS = ["-", "https://lagrange-cuisine.example/"]


def build_ips():
    """Renvoie 30 IP de documentation : 10 dans chacune des 3 plages RFC 5737."""
    ips = []
    for prefix in ["192.0.2.", "198.51.100.", "203.0.113."]:
        for i in range(1, 11):
            ips.append(f"{prefix}{i}")
    return ips


def pick_status(rng, path, in_peak):
    """Choisit le code HTTP d'une requête.

    rng     : l'objet random.Random (utiliser rng.random(), jamais random.random())
    path    : la route demandée, ex. "/api/payment"
    in_peak : True si la requête tombe dans la minute du pic
    Renvoie un int : 200, 404, 502...
    """
    
    if in_peak and rng.random() < 0.3:
        return 502
    if rng.random() < 0.01:
        return 500
    return 200


def make_line(rng, ips, time, in_peak):
    """Renvoie une ligne au format nginx combined + $request_time (docs/conception.md §3)."""
    if rng.random() < 0.2:
        ip = ips[0]                 # un client très actif : le top IP sera parlant
    else:
        ip = rng.choice(ips)

    path = rng.choice(ROUTES)
    if path == "/api/payment":
        method = "POST"
    else:
        method = "GET"

    status = pick_status(rng, path, in_peak)

    url = path
    if path == "/api/orders" and rng.random() < 0.5:
        url = f"{path}?id={rng.randint(1, 9999)}"   # logwatch doit retirer la query string

    if status >= 500:
        latency = rng.uniform(1.0, 30.0)   # une erreur serveur est souvent lente (timeout)
        size = rng.randint(150, 600)
    else:
        latency = rng.uniform(0.01, 0.3)
        size = rng.randint(200, 50000)

    referer = rng.choice(REFERERS)
    agent = rng.choice(USER_AGENTS)
    return (f'{ip} - - [{DAY}:{time} {TIMEZONE}] "{method} {url} HTTP/1.1" '
            f'{status} {size} "{referer}" "{agent}" {latency:.3f}')


def make_invalid_line(number, previous_line):
    """Renvoie une ligne abîmée. On alterne 4 sortes, d'après le numéro."""
    kind = number % 4
    if kind == 0:
        return ""                                        # ligne vide
    elif kind == 1:
        return previous_line[:40]                        # ligne tronquée
    elif kind == 2:
        return "garbage line without structure"          # aucune structure
    else:
        return " ".join(previous_line.split(" ")[:-1])   # latence manquante


def generate(path, peak_minute):
    """Écrit un log complet dans path. peak_minute : "02:07", ou None pour un log calme.

    Renvoie le tuple (lignes valides, lignes abîmées).
    """
    rng = random.Random(SEED)
    ips = build_ips()
    valid = 0
    invalid = 0

    with open(path, "w", encoding="utf-8") as f:
        for m in range(DURATION):
            total = START_HOUR * 60 + START_MINUTE + m       # minutes depuis minuit
            minute = f"{total // 60:02d}:{total % 60:02d}"   # ex. 127 -> "02:07"
            in_peak = minute == peak_minute

            # Secondes triées : un vrai log est dans l'ordre chronologique.
            seconds = sorted(rng.randint(0, 59) for _ in range(LINES_PER_MINUTE))
            for second in seconds:
                line = make_line(rng, ips, f"{minute}:{second:02d}", in_peak)
                f.write(line + "\n")
                valid += 1
                if valid % INVALID_EVERY == 0:
                    f.write(make_invalid_line(invalid, line) + "\n")
                    invalid += 1

    return valid, invalid


def main():
    for path, peak in [(DATA_DIR / "incident.log", PEAK_MINUTE), (DATA_DIR / "calme.log", None)]:
        try:
            valid, invalid = generate(path, peak)
        except OSError as e:
            print(f"impossible d'écrire {path} : {e}")
            return 2
        print(f"{path} : {valid} lignes valides, {invalid} abîmées, pic : {peak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
