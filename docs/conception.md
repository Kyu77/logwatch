# logwatch — Document de conception

_Version 2 — 25/11/2026 : alignée sur le code des étapes 2 à 6. Sera mise à jour avec la version finale avant le rendu._

## 1. Objectif

`logwatch` lit un fichier de log nginx (format *combined* suivi de `$request_time`),
calcule des indicateurs de santé du site, détecte les minutes où le taux d'erreurs
5xx dépasse un seuil et, sur demande (`--alert`), prévient l'astreinte par webhook.

Public visé : l'astreinte et l'équipe technique de Lagrange Cuisine. La nuit de la
Black Week, une panne de paiement (502) a duré 35 minutes sans alerte, et le
post-mortem n'a pu conclure que « vers 2 h ». `logwatch` doit répondre en une
commande à « que s'est-il passé cette nuit », avec un simple accès SSH, et donner
la minute exacte des pics.

Hors périmètre : plateforme de logs (ELK, Loki) et supervision continue.

## 2. Schéma des modules et du flux

Le code est découpé en un fichier par rôle. Chacun peut travailler sur son
fichier sans conflit git, et `logwatch.py` relie le tout :

```
        argv              logwatch.json / --config (optionnel)
          │                         │
          ▼                         ▼
   config_cli.parse_args()   config_cli.load_config()
          └──────────┬──────────────┘
                     ▼
         config_cli.merge_config()      priorité : CLI > config > défauts
                     │
                     ▼
         logparser.read_logs()          regex, ligne par ligne,
                     │                  lignes invalides comptées (5 en échantillon)
                     ▼
         logstats.compute_stats()       volume, taux 5xx/4xx, tops, latences,
                     │                  agrégation par minute, pics
                     ▼
         report.get_exit_code()         0 aucun pic / 1 au moins un pic
                     │
                     ▼  (si --alert ET au moins un pic)
         send_alert()                   POST vers LOGWATCH_WEBHOOK_URL
                     │
                     ▼
         report.build_report() + write_report()   JSON ou texte, fichier ou stdout
```

| Fichier | Fonctions | Rôle | Auteur |
|---|---|---|---|
| `generate_logs.py` | `generate` | fabrique `data/incident.log` et `data/calme.log` | Hugo |
| `logparser.py` | `read_logs`, `new_stats` | regex, lecture ligne à ligne, lignes invalides, `exclude_paths` | Christopher |
| `config_cli.py` | `parse_args`, `load_config`, `merge_config`, `setup_logging` | CLI, config JSON validée, priorité, logging | Christopher |
| `logstats.py` | `compute_stats` | indicateurs, agrégation par minute, pics | Hugo |
| `report.py` | `get_exit_code`, `build_report`, `to_text`, `write_report` | rapport JSON / texte, code 0 ou 1 | Hugo |
| `logwatch.py` | `main`, `send_alert` | relie les fichiers, webhook, code 2 en cas d'erreur | à faire |

## 3. Format d'entrée

Une ligne nginx *combined* + `$request_time` :

```
203.0.113.7 - - [20/Nov/2026:02:07:13 +0100] "GET /api/orders?id=4 HTTP/1.1" 502 157 "-" "curl/8.5" 0.342
```

Champs gardés pour chaque requête valide : IP, minute (`20/Nov/2026:02:07`),
route sans query string (`/api/orders`), code HTTP, latence en secondes.
La méthode (GET, POST) est reconnue par la regex mais n'est pas gardée : le
rapport n'en a pas besoin.

## 4. Format de la configuration

Fichier JSON (voir `config.example.json`) :

| Clé | Type | Défaut | Contrainte |
|---|---|---|---|
| `threshold_5xx` | float | 0.05 | 0 ≤ x ≤ 1 (taux 5xx dans la minute) |
| `min_requests` | int | 50 | ≥ 1 (requêtes minimum dans la minute pour être un pic) |
| `top_n` | int | 10 | ≥ 1 |
| `exclude_paths` | list[str] | `["/health", "/metrics"]` | chaque élément est une chaîne non vide |
| `webhook_timeout_s` | float | 5 | > 0 |

Une clé inconnue dans le fichier est refusée. Les clés absentes prennent la
valeur par défaut.

Fichier lu : `--config` s'il est donné, sinon `logwatch.json` s'il existe, sinon
les valeurs par défaut.

Priorité : **option CLI > fichier de config > valeur par défaut**
(`--threshold` remplace `threshold_5xx`, `--top` remplace `top_n`).

Options CLI : fichier (positionnel), `--config`, `--threshold`, `--top`,
`--format json|text` (défaut `text`), `--output` (défaut stdout), `--alert`,
`--verbose` (logs DEBUG au lieu de INFO).
Toute clé de type ou de valeur incohérente → message d'erreur et code 2.
L'URL du webhook n'est **jamais** dans la config : uniquement dans la variable
d'environnement `LOGWATCH_WEBHOOK_URL`.

## 5. Format du rapport

Rapport JSON (le rapport texte présente les mêmes informations de façon lisible) :

```json
{
  "tool": "logwatch",
  "source": "data/incident.log",
  "lines": { "valid": 9980, "invalid": 20, "invalid_samples": ["garbage line without structure"] },
  "summary": { "requests": 9980, "rate_5xx": 0.012, "rate_4xx": 0.041,
               "latency_s": { "mean": 0.092, "p95": 0.480, "max": 30.001 } },
  "top_ips":   [ { "ip": "198.51.100.23", "requests": 912 } ],
  "top_paths": [ { "path": "/api/orders", "requests": 4021 } ],
  "peaks":     [ { "minute": "20/Nov/2026:02:07", "requests": 190, "rate_5xx": 0.18 } ],
  "alert_sent": false,
  "exit_code": 1
}
```

_Valeurs d'exemple, pas un résultat mesuré._ `invalid_samples` contient au plus
les 5 premières lignes invalides.

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
- Le p95 suit la règle du sujet (`int(0.95 * len)`) : sur très peu de requêtes,
  il est égal au maximum.
- Les données de test ne contiennent pas de 4xx : le taux 4xx vaut 0 dans nos tests.
