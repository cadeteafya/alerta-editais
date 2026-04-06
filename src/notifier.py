import os
import requests
import logging

logger = logging.getLogger(__name__)

FALLBACK_URL = "https://portal-residencia.vercel.app/tools/editais/index.html"

def send_teams_notification(edital_info: dict, paragraph: str, link: str, article_title: str = "", action_links: list = None):
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logger.error("TEAMS_WEBHOOK_URL is not set.")
        return False

    instituicao = edital_info.get("instituicao", "Não informada")
    tipo = edital_info.get("tipo", "novo_edital")

    # Cabeçalho dinâmico baseado na classificação da IA
    if tipo == "atualizacao":
        card_header = "💡 NOVAS INFORMAÇÕES!"
        card_color = "Accent"
    else:
        card_header = "🚨 NOVO EDITAL DE RESIDÊNCIA MÉDICA"
        card_color = "Attention"

    # ---- Corpo do card ----
    body_items = [
        {
            "type": "Container",
            "style": "emphasis",
            "items": [{
                "type": "TextBlock",
                "text": card_header,
                "weight": "Bolder",
                "size": "Medium",
                "color": card_color,
                "wrap": True
            }]
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "🏥 Instituição", "value": instituicao}
            ]
        }
    ]

    if tipo == "atualizacao":
        # Atualizações: título do artigo em destaque + parágrafo. Sem botões.
        if article_title:
            body_items.append({
                "type": "TextBlock",
                "text": article_title,
                "weight": "Bolder",
                "wrap": True,
                "spacing": "Medium"
            })
        body_items.append({
            "type": "TextBlock",
            "text": paragraph,
            "wrap": True,
            "spacing": "Small"
        })
        actions = []
    else:
        # Editais novos: apenas parágrafo + 1 botão externo
        body_items.append({
            "type": "TextBlock",
            "text": paragraph,
            "wrap": True,
            "spacing": "Medium"
        })

        # Busca o primeiro link que NÃO seja do med.estrategia e NÃO seja botão de PDF
        banca_url = None
        if action_links:
            seen_urls = set()
            for link_obj in action_links:
                title_link = (link_obj.get("title") or "").strip().upper()
                url = (link_obj.get("url") or "").strip()
                is_edital_btn = 'EDITAL' in title_link or 'RETIFICA' in title_link
                is_estrategia = 'med.estrategia' in url or 'estrategiaeducacional' in url
                if not url or url in seen_urls or is_edital_btn or is_estrategia:
                    continue
                seen_urls.add(url)
                banca_url = url
                break

        if banca_url:
            actions = [{
                "type": "Action.OpenUrl",
                "title": "🌐 PÁGINA OFICIAL DA BANCA",
                "url": banca_url
            }]
        else:
            actions = [{
                "type": "Action.OpenUrl",
                "title": "📋 NOSSA PÁGINA DE EDITAIS",
                "url": FALLBACK_URL
            }]

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body_items,
                    "actions": actions
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Notification sent to Teams for {instituicao} [{tipo}]")
        return True
    except Exception as e:
        logger.error(f"Error sending Teams notification: {e}")
        return False