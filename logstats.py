"""logstats.py : étape 4, calcul des indicateurs et détection des pics.

Reçoit les requêtes valides produites par logparser.read_logs(), une par une.
Chaque requête est un dict :
    {"ip": "192.0.2.5", "minute": "20/Nov/2026:02:07", "path": "/api/orders",
     "status": 502, "latency": 1.234}
"""

from collections import Counter


def p95(latencies):
    """Renvoie le 95e centile : 95 % des requêtes ont répondu plus vite que ça.

    Règle du sujet : on trie la liste et on prend l'élément à l'indice int(0.95 * len).
    """
    if not latencies:
        return 0.0
    tri = sorted(latencies)
    return tri[int(0.95 * len(tri))]


def compute_stats(entries, threshold_5xx, min_requests, top_n):
    """Parcourt les requêtes une seule fois et calcule tous les indicateurs.

    entries       : les requêtes valides (liste ou générateur de dicts)
    threshold_5xx : taux de 5xx au-dessus duquel une minute est en pic (ex. 0.05)
    min_requests  : nombre minimum de requêtes dans la minute pour parler de pic
    top_n         : nombre d'IP et de routes à garder dans les tops

    Renvoie un dict avec les clés "summary", "top_ips", "top_paths" et "peaks",
    au format du rapport décrit dans docs/conception.md.
    """
    requests = 0            # volume : nombre de requêtes valides
    count_5xx = 0           # erreurs serveur (500 à 599) : ce sont les pannes
    count_4xx = 0           # erreurs du client (400 à 499) : comptées à part
    ips = Counter()         # Counter = un dict qui compte : ips["192.0.2.5"] -> 1830
    paths = Counter()
    latencies = []          # toutes les latences, nécessaires pour le p95
    minutes = {}            # "20/Nov/2026:02:07" -> {"requests": 166, "errors_5xx": 52}

    for entry in entries:
        requests += 1
        status = entry["status"]
        is_5xx = 500 <= status <= 599
        if is_5xx:
            count_5xx += 1
        elif 400 <= status <= 499:
            count_4xx += 1

        ips[entry["ip"]] += 1
        paths[entry["path"]] += 1
        latencies.append(entry["latency"])

        # Agrégation par minute : la chaîne de la minute suffit comme clé.
        minute = entry["minute"]
        if minute not in minutes:
            minutes[minute] = {"requests": 0, "errors_5xx": 0}
        minutes[minute]["requests"] += 1
        if is_5xx:
            minutes[minute]["errors_5xx"] += 1

    # Aucune requête valide : on renvoie des zéros (pas de division par zéro).
    # C'est main() qui transformera ce cas en code de sortie 2.
    if requests == 0:
        return {
            "summary": {"requests": 0, "rate_5xx": 0.0, "rate_4xx": 0.0,
                        "latency_s": {"mean": 0.0, "p95": 0.0, "max": 0.0}},
            "top_ips": [],
            "top_paths": [],
            "peaks": [],
        }

    # Détection des pics. Deux conditions, toutes les deux obligatoires :
    #   1. assez de requêtes dans la minute (sinon 1 erreur sur 2 = 50 %, faux pic)
    #   2. taux de 5xx strictement au-dessus du seuil
    # Le dict garde l'ordre d'insertion, donc les minutes sortent dans l'ordre du fichier.
    peaks = []
    for minute, counts in minutes.items():
        rate = counts["errors_5xx"] / counts["requests"]
        if counts["requests"] >= min_requests and rate > threshold_5xx:
            peaks.append({
                "minute": minute,
                "requests": counts["requests"],
                "rate_5xx": round(rate, 3),
            })

    return {
        "summary": {
            "requests": requests,
            "rate_5xx": round(count_5xx / requests, 3),
            "rate_4xx": round(count_4xx / requests, 3),
            "latency_s": {
                "mean": round(sum(latencies) / requests, 3),
                "p95": round(p95(latencies), 3),
                "max": round(max(latencies), 3),
            },
        },
        # most_common(n) renvoie les n paires (clé, compteur) les plus fréquentes.
        "top_ips": [{"ip": ip, "requests": n} for ip, n in ips.most_common(top_n)],
        "top_paths": [{"path": path, "requests": n} for path, n in paths.most_common(top_n)],
        "peaks": peaks,
    }
