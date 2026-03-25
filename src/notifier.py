import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_teams_notification(edital_info: dict, paragraph: str, link: str):
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logger.error("TEAMS_WEBHOOK_URL is not set.")
        return False

    instituicao = edital_info.get("instituicao", "Não informada")
    tipo = edital_info.get("tipo", "Não informado")

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "🚨 NOVO EDITAL DE RESIDÊNCIA MÉDICA",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Attention",
                                    "wrap": True
                                }
                            ]
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "🏥 Instituição", "value": instituicao},
                                {"title": "📋 Tipo", "value": tipo}
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": paragraph,
                            "wrap": True,
                            "spacing": "Medium"
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "📄 Ver Edital Completo",
                            "url": link
                        }
                    ]
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Notification sent to Teams for {instituicao}")
        return True
    except Exception as e:
        logger.error(f"Error sending Teams notification: {e}")
        return False
        