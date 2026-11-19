from collections import Counter


# Calcule les indicateurs à partir des requêtes données par read_logs()
def compute_stats(entries, threshold_5xx, min_requests, top_n):
    requests = 0
    count_5xx = 0
    count_4xx = 0
    ips = Counter()
    paths = Counter()
    latencies = []
    minutes = {}   # ex : {"20/Nov/2026:02:07": {"requests": 143, "errors_5xx": 48}}

    for entry in entries:
        requests += 1
        ips[entry["ip"]] += 1
        paths[entry["path"]] += 1
        latencies.append(entry["latency"])

        minute = entry["minute"]
        if minute not in minutes:
            minutes[minute] = {"requests": 0, "errors_5xx": 0}
        minutes[minute]["requests"] += 1

        if entry["status"] >= 500:
            count_5xx += 1
            minutes[minute]["errors_5xx"] += 1
        elif entry["status"] >= 400:
            count_4xx += 1

    # Aucune requête valide : main() renverra le code 2
    if requests == 0:
        return None

    # Une minute est un pic si elle a assez de requêtes ET trop de 5xx
    peaks = []
    for minute, counts in minutes.items():
        rate = counts["errors_5xx"] / counts["requests"]
        if counts["requests"] >= min_requests and rate > threshold_5xx:
            peaks.append({"minute": minute, "requests": counts["requests"], "rate_5xx": round(rate, 3)})

    top_ips = []
    for ip, n in ips.most_common(top_n):
        top_ips.append({"ip": ip, "requests": n})

    top_paths = []
    for path, n in paths.most_common(top_n):
        top_paths.append({"path": path, "requests": n})

    # p95 : on trie les latences et on prend celle à 95 % de la liste
    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies))]

    return {
        "summary": {
            "requests": requests,
            "rate_5xx": round(count_5xx / requests, 3),
            "rate_4xx": round(count_4xx / requests, 3),
            "latency_s": {
                "mean": round(sum(latencies) / requests, 3),
                "p95": round(p95, 3),
                "max": round(max(latencies), 3),
            },
        },
        "top_ips": top_ips,
        "top_paths": top_paths,
        "peaks": peaks,
    }
