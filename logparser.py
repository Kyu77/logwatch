import re
import logging

logger = logging.getLogger(__name__)

# Découpage des lignes des fichiers de logs pour que chaque élément puisse être lu sans problème
LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ '
    r'\[(?P<date>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<url>\S+) [^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) '
    r'"[^"]*" "[^"]*" '
    r'(?P<latency>\d+(?:\.\d+)?)$'
)

# Fonction qui permet de renvoyer un dictionnaire avec ces valeurs à 0 + une liste vide qui recevra les lignes invalides
def new_stats():
    return {"valid": 0, "invalid": 0, "excluded": 0, "invalid_samples": []}

# Fonction qui lit les fichiers de logs 
# Avant de passer stats en paramètre, bien veiller à faire stats = new_stats() pour qu'il soit déjà un dict avec les bonnes clés !
# Exclude_paths représente les chemins à exclure, ça pourra être juste une liste contenant les uri à exclure, ex : /health ...
def read_logs(chemin, exclude_paths, stats):
    with open(chemin, "r", encoding="utf-8", errors="replace") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.rstrip("\n")

            m = LOG_RE.match(line)
            if m is None:
                # Ligne invalide qu'on compte et on garde les 5 premières
                logger.debug("ligne %d invalide : %r", line_number, line) 
                stats["invalid"] += 1
                if len(stats["invalid_samples"]) < 5:
                    stats["invalid_samples"].append(line)
                continue

            # Ici on retire les query string des lignes, le ? qu'il y a dans les chemins
            path = m["url"].split("?")[0]
            if path in exclude_paths:
                stats["excluded"] += 1
                continue

            stats["valid"] += 1
            # yield renvoie la requête valide, puis reprend la lecture à la ligne suivante.
            yield {
                "ip": m["ip"],
                "minute": m["date"][:17],
                "path": path,
                "status": int(m["status"]),
                "latency": float(m["latency"]),
            }