import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_teams_notification(edital_info: dict, paragraph: str, link: str, action_links: list = None):
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logger.error("TEAMS_WEBHOOK_URL is not set.")
        return False

    instituicao = edital_info.get("instituicao", "Não informada")
    tipo = edital_info.get("tipo", "Não informado")

    # Construir lista de botões dinâmica
    actions = []
    has_banca_link = False
    
    if action_links:
        # Remover duplicatas mantendo a ordem (caso a API do WP retorne o mesmo link do edital e da banca em tags diferentes no mesmo 'name')
        seen_urls = set()
        for link_obj in action_links:
            title = link_obj.get("title", "").strip()
            url = link_obj.get("url", "").strip()
            
            if not title or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Se for edital:
            if 'EDITAL' in title.upper() or 'RETIFICA' in title.upper():
                btn_title = f"📄 {title}"
            else:
                has_banca_link = True
                btn_title = f"🌐 {title}"
                
            actions.append({
                "type": "Action.OpenUrl",
                "title": btn_title,
                "url": url
            })
            
    # Fallback obrigatório: se não achou link de banca
    if not has_banca_link:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "🌐 PÁGINA OFICIAL DA BANCA",
            "url": "https://portal-residencia.vercel.app/tools/editais/index.html"
        })

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
                    "actions": actions
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