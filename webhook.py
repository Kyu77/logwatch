import os
import logging
import requests

logger = logging.getLogger(__name__)

# Lève l'erreur si LOGWATCH_WEBHOOK_URL est absente
class WebhookConfigError(Exception):
    pass


# Envoie l'alerte webhook. Renvoie True si elle est partie, False sinon.
# peaks : liste de dicts {"minute", "requests", "rate_5xx"}
# config : dict de config déjà validé (on y lit webhook_timeout_s)
# alert_requested : True si --alert a été passé
def send_alert(peaks, config, alert_requested):

    # Sans --alert, rien ne part, jamais
    if not alert_requested:
        return False

    # L'URL est un secret : lue uniquement dans l'environnement, jamais loggée
    webhook_url = os.environ.get("LOGWATCH_WEBHOOK_URL")
    if not webhook_url:
        raise WebhookConfigError("LOGWATCH_WEBHOOK_URL n'est pas défini")

    # --alert demandé mais aucun pic : pas d'alerte
    if not peaks:
        logger.info("Aucun pic : pas d'alerte envoyée")
        return False

    # Message utile pour l'astreinte : nombre de pics + le pire
    worst = max(peaks, key=lambda p: p["rate_5xx"])
    payload = {

        # "content" en minuscules = format Discord
        "content": (
            f"logwatch : {len(peaks)} minute(s) en pic de 5xx. "
            f"Pire : {worst['minute']} ({worst['rate_5xx']:.0%} sur "
            f"{worst['requests']} requêtes)."
        )
    }

    try:
        # Le timeout évite de rester bloqué si le serveur ne répond pas
        response = requests.post(
            webhook_url, 
            json=payload, 
            timeout=config.get("webhook_timeout_s", 5)
        )

        # Exception si le code HTTP est 4xx ou 5xx
        response.raise_for_status()
    except requests.exceptions.RequestException as e:

        # On logue seulement le type d'erreur : e peut contenir l'URL (secret)
        # Le code de sortie reste 1 : le pic existe, seule l'alerte a échoué
        logger.error("Échec de l'envoi de l'alerte : %s", type(e).__name__)
        return False

    logger.info("Alerte envoyée (HTTP %d)", response.status_code)
    return True
