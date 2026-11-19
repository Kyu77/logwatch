import json


# 1 s'il y a au moins un pic, sinon 0
def get_exit_code(stats):
    if len(stats["peaks"]) > 0:
        return 1
    return 0


# Assemble le rapport au format du sujet
def build_report(source, parse_stats, stats, alert_sent, exit_code):
    report = {
        "tool": "logwatch",
        "source": source,
        "lines": {
            "valid": parse_stats["valid"],
            "invalid": parse_stats["invalid"],
            "invalid_samples": parse_stats["invalid_samples"],
        },
        "summary": stats["summary"],
        "top_ips": stats["top_ips"],
        "top_paths": stats["top_paths"],
        "peaks": stats["peaks"],
        "alert_sent": alert_sent,
        "exit_code": exit_code,
    }
    return report


# Rapport lisible par un humain
def to_text(report):
    text = "logwatch - " + report["source"] + "\n"
    text += "Lignes valides : " + str(report["lines"]["valid"]) + "\n"
    text += "Lignes invalides : " + str(report["lines"]["invalid"]) + "\n"
    text += "Taux 5xx : " + str(report["summary"]["rate_5xx"]) + "\n"
    text += "Taux 4xx : " + str(report["summary"]["rate_4xx"]) + "\n"
    text += "Latence moyenne : " + str(report["summary"]["latency_s"]["mean"]) + " s\n"
    text += "Latence p95 : " + str(report["summary"]["latency_s"]["p95"]) + " s\n"
    text += "Latence max : " + str(report["summary"]["latency_s"]["max"]) + " s\n"

    text += "Top IP :\n"
    for item in report["top_ips"]:
        text += "  " + item["ip"] + " : " + str(item["requests"]) + "\n"

    text += "Top routes :\n"
    for item in report["top_paths"]:
        text += "  " + item["path"] + " : " + str(item["requests"]) + "\n"

    text += "Pics :\n"
    if len(report["peaks"]) == 0:
        text += "  aucun\n"
    for peak in report["peaks"]:
        text += "  " + peak["minute"] + " : taux 5xx " + str(peak["rate_5xx"]) + "\n"

    text += "Code de sortie : " + str(report["exit_code"])
    return text


# Écrit le rapport dans un fichier si output est donné, sinon à l'écran
def write_report(report, fmt, output):
    if fmt == "json":
        content = json.dumps(report, indent=2)
    else:
        content = to_text(report)

    if output is None:
        print(content)
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
