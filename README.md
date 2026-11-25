# logwatch

Outil en ligne de commande qui lit un log nginx, calcule la santé du site
(volume, erreurs, top IP/routes, latences), détecte les minutes en pic d'erreurs
5xx et peut prévenir l'astreinte par webhook.

> Projet en cours — voir [docs/conception.md](docs/conception.md) pour la conception.

## Installation

Prérequis : Python 3.14.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

## Organisation du code

| Fichier | Rôle |
|---|---|
| `generate_logs.py` | fabrique les données de test `data/incident.log` (pic à 02:07) et `data/calme.log` |
| `logparser.py` | lit le log ligne par ligne et découpe chaque ligne avec une regex |
| `config_cli.py` | options de la ligne de commande et configuration JSON |
| `logstats.py` | calcule les indicateurs et détecte les pics |
| `report.py` | produit le rapport JSON ou texte et le code de sortie |
| `logwatch.py` | point d'entrée : relie les fichiers (en cours) |

## Utilisation (cible)

```bash
python logwatch.py data/incident.log --config config.example.json --top 10 --format json --output reports/incident.json
```

_Exemple de sortie : à ajouter quand `logwatch.py` sera terminé._

Pour régénérer les données de test :

```bash
python generate_logs.py
```

## Configuration

Copier `config.example.json` en `logwatch.json` pour l'utiliser par défaut
(`logwatch.json` est ignoré par git). Sans fichier, les valeurs par défaut s'appliquent.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `LOGWATCH_WEBHOOK_URL` | URL du webhook d'alerte (obligatoire avec `--alert`, jamais commitée) |

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | aucun pic |
| 1 | au moins une minute en pic |
| 2 | fichier absent/illisible, aucune ligne valide, config invalide, `--alert` sans variable d'environnement |

## Répartition du travail

| Hugo | Christopher |
|---|---|
| Générateur et données de test (`generate_logs.py`) | Regex et parsing des lignes (`logparser.py`) |
| Calcul des indicateurs et des pics (`logstats.py`) | Config JSON, validation, CLI argparse, logging (`config_cli.py`) |
| Rapport JSON/texte et codes de sortie (`report.py`) | |
| _à répartir : `main()`, webhook, pipeline CI, extension « incidents »_ | |

Ensemble : README, `docs/conception.md`, revue croisée du code, préparation de la soutenance.

## Limites

- Un seul format de log : nginx combined suivi de `$request_time`.
- Toutes les latences sont gardées en mémoire pour le p95.
- Les minutes sont des chaînes : pas de gestion des fuseaux horaires.
- Une minute avec moins de `min_requests` requêtes n'est jamais un pic.
- Pas de logs rotés ou compressés, pas de nouvelle tentative du webhook.

Détail dans [docs/conception.md](docs/conception.md#8-limites-connues).
