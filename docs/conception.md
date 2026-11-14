# logwatch — Document de conception (v1)

_Version 1 — 17/11/2026. Sera mise à jour avec la version finale avant le rendu._

## 1. Objectif

`logwatch` lit un fichier de log nginx (format *combined* suivi de `$request_time`),
calcule des indicateurs de santé du site, détecte les minutes où le taux d'erreurs
5xx dépasse un seuil et, sur demande (`--alert`), prévient l'astreinte par webhook.

Public visé : l'équipe d'astreinte / exploitation, qui veut un diagnostic rapide
d'un incident à partir d'un fichier de log, en local ou dans une CI.

## 2. Schéma des modules et du flux

Le code est dans un seul fichier `logwatch.py`, découpé en fonctions à
responsabilité unique :

```
            argv                     config.json (optionnel)
              │                              │
              ▼                              ▼
        parse_args() ───────────────► load_config()
              │        fusion : CLI > config > défauts
              ▼
         read_log(path)  ──► parse_line(line)  (regex, ligne par ligne)
              │                 │
              │                 └─ ligne invalide : comptée + 5 premières en échantillon
              ▼
       compute_stats(entries)
         ├─ volume, taux 4xx, taux 5xx
         ├─ top N IP / top N routes
         ├─ latences : moyenne, p95, max
         └─ agrégation par minute ──► détection des pics
              │
              ▼
       build_report()  ──► JSON ou texte ──► fichier (--output) ou stdout
              │
              ▼  (si --alert ET au moins un pic)
       send_alert()  ──► POST LOGWATCH_WEBHOOK_URL
              │
              ▼
          code de sortie (0 / 1 / 2)
```

| Fonction | Rôle | Responsable |
|---|---|---|
| `parse_args` | options CLI (argparse) | B |
| `load_config` | lecture + validation JSON | B |
| `parse_line` / `read_log` | regex, lecture ligne à ligne, lignes invalides, `exclude_paths` | A |
| `compute_stats` | indicateurs, agrégation par minute, pics | A |
| `build_report` | rapport JSON / texte | B |
| `send_alert` | webhook | B |
| `main` | orchestration, logging, codes de sortie | A + B |

## 3. Format d'entrée

Une ligne nginx *combined* + `$request_time` :

```
203.0.113.7 - - [20/Nov/2026:02:07:13 +0100] "GET /api/orders?id=4 HTTP/1.1" 502 157 "-" "curl/8.5" 0.342
```

Champs extraits : IP, minute (`20/Nov/2026:02:07`), méthode, route sans query
string (`/api/orders`), code HTTP, latence en secondes.

## 4. Format de la configuration

Fichier JSON (voir `config.example.json`) :

| Clé | Type | Défaut | Contrainte |
|---|---|---|---|
| `threshold` | float | 0.05 | 0 < x ≤ 1 (taux 5xx dans la minute) |
| `min_requests` | int | 20 | ≥ 1 (requêtes minimum dans la minute pour être un pic) |
| `top` | int | 5 | ≥ 1 |
| `format` | str | `"text"` | `"json"` ou `"text"` |
| `exclude_paths` | list[str] | `["/health", "/metrics"]` | chaque élément commence par `/` |
| `webhook_timeout_s` | float | 5 | > 0 |

Priorité : **option CLI > fichier de config > valeur par défaut**.
Toute clé de type ou de valeur incohérente → message d'erreur et code 2.
L'URL du webhook n'est **jamais** dans la config : uniquement dans la variable
d'environnement `LOGWATCH_WEBHOOK_URL`.

## 5. Format du rapport

Rapport JSON (le rapport texte présente les mêmes informations de façon lisible) :

```json
{
  "lines": {"total": 1203, "valid": 1198, "invalid": 5, "excluded": 40,
            "invalid_samples": ["...", "..."]},
  "summary": {"requests": 1158, "rate_5xx": 0.031, "rate_4xx": 0.012,
              "latency_avg": 0.118, "latency_p95": 0.402, "latency_max": 2.31},
  "top_ips":   [{"ip": "203.0.113.7", "count": 210}],
  "top_paths": [{"path": "/api/orders", "count": 340}],
  "peaks": [{"minute": "20/Nov/2026:02:07", "requests": 48, "errors_5xx": 19, "rate_5xx": 0.396}],
  "alert_sent": false,
  "exit_code": 1
}
```

_Le format exact sera aligné sur l'exemple du sujet._

## 6. Codes de sortie

| Code | Cas |
|---|---|
| 0 | analyse réussie, aucun pic |
| 1 | au moins une minute en pic (même si l'envoi du webhook échoue) |
| 2 | fichier absent/illisible, aucune ligne valide, config invalide, `--alert` sans `LOGWATCH_WEBHOOK_URL` |

## 7. Choix techniques justifiés

1. **Lecture ligne à ligne (`for line in f`) plutôt que `read()` / `readlines()`.**
   Un log de production peut peser plusieurs Go : l'itération sur le fichier garde
   une mémoire constante pour la lecture. Une ligne abîmée est simplement comptée
   et ignorée, l'analyse continue.

2. **Agrégation par minute avec la chaîne `20/Nov/2026:02:07` comme clé d'un dict,
   sans conversion en `datetime`.** C'est suffisant pour regrouper et détecter les
   pics, plus simple et plus rapide qu'un parsing de date à chaque ligne. Le
   parsing en `datetime` (avec fuseau) ne sera ajouté que pour les extensions
   `--since` / `--until`.

3. **(Choix à défendre) Échec du webhook → log ERROR mais code de sortie 1 conservé.**
   Le code de sortie décrit l'état du site (il y a un pic), pas la réussite de la
   notification ; un code 2 masquerait l'incident pour une CI ou un script appelant.

## 8. Limites connues

- Un seul format de log supporté (nginx combined + `$request_time`) ; un autre
  `log_format` rend toutes les lignes invalides.
- Le p95 est calculé en gardant toutes les latences en mémoire (liste triée) :
  la mémoire croît avec le nombre de requêtes.
- Les clés de minute sont des chaînes : pas de gestion des fuseaux horaires ni des
  changements d'heure ; l'ordre chronologique repose sur l'ordre du fichier.
- Une minute avec moins de `min_requests` requêtes n'est jamais un pic, même à 100 % de 5xx.
- Pas de lecture des logs rotés ni compressés dans le socle (extension prévue).
- Pas de nouvelle tentative si le webhook échoue.
