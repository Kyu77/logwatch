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

## Utilisation (cible)

```bash
python logwatch.py data/incident.log --config config.example.json --top 10 --format json --output reports/incident.json
```

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

| Personne A | Personne B |
|---|---|
| Générateur et données de test | Config JSON + validation |
| Regex et parsing des lignes | CLI argparse + logging |
| Calcul des indicateurs et des pics | Rapport JSON/texte + codes de sortie |
| Extension 1 (incidents) | Webhook + pipeline CI |

Ensemble : README, `docs/conception.md`, revue croisée du code, préparation de la soutenance.

## Limites

_À compléter._

## Usage de l'IA

_À compléter : outils utilisés, pour quoi, ce qui a été repris ou réécrit, au moins une erreur de l'IA repérée._
