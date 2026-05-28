import os
import requests
import logging

logger = logging.getLogger(__name__)

TRACKER_URL = "https://edital-tracker-woad.vercel.app/"

def send_teams_notification(edital: dict) -> bool:
    """Envia uma notificação premium via Microsoft Teams Adaptive Cards com dados estruturados do edital."""
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logger.error("TEAMS_WEBHOOK_URL is not set.")
        return False

    title = edital.get("title", "Edital")
    institution = edital.get("institution", "Não informada")
    year = edital.get("year", "2026")
    tag = edital.get("tag", "")
    published_at = edital.get("published_at", "Data não informada")
    next_milestone = edital.get("next_milestone", {})
    schedule = edital.get("schedule", [])
    official_link = edital.get("official_link")

    # Determinar a urgência/estilo do cabeçalho
    tag_upper = tag.upper()
    is_new_edital = "SAIU" in tag_upper or "NOVO" in tag_upper or "EDITAL" in tag_upper
    
    if is_new_edital:
        card_header = f"🚨 NOVO EDITAL: {institution} {year}"
        card_color = "Attention" # Vermelho/Laranja de alerta
    else:
        card_header = f"🔔 ATUALIZAÇÃO: {institution} {year}"
        card_color = "Accent" # Azul informativo

    # ---- Cabeçalho e Metadados ----
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
            "type": "TextBlock",
            "text": title,
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
            "spacing": "Medium"
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "🏥 Instituição", "value": institution},
                {"title": "📅 Publicado em", "value": published_at}
            ],
            "spacing": "Small"
        }
    ]

    # ---- Destaque do Próximo Marco ----
    if next_milestone and next_milestone.get("stage"):
        stage_name = next_milestone["stage"]
        stage_date = next_milestone["date"]
        time_left = next_milestone["time_left"]
        time_str = f" ({time_left})" if time_left else ""
        
        body_items.append({
            "type": "Container",
            "style": "accent",
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "🚀 PRÓXIMO MARCO EM DESTAQUE",
                    "weight": "Bolder",
                    "size": "Small",
                    "color": "Accent",
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": stage_name, "value": f"{stage_date}{time_str}"}
                    ]
                }
            ]
        })

    # ---- Cronograma de Eventos ----
    if schedule:
        schedule_facts = []
        max_lines = 10
        
        if len(schedule) > max_lines:
            # Exibe os primeiros 9 itens e coloca o aviso de limite na 10ª linha
            for item in schedule[:max_lines - 1]:
                schedule_facts.append({
                    "title": item["stage"],
                    "value": item["date"]
                })
            schedule_facts.append({
                "title": "⚠️ Cronograma",
                "value": "Cronograma muito longo. Conferir diretamente no site."
            })
        else:
            for item in schedule:
                schedule_facts.append({
                    "title": item["stage"],
                    "value": item["date"]
                })

        body_items.append({
            "type": "TextBlock",
            "text": "📅 Cronograma Completo:",
            "weight": "Bolder",
            "spacing": "Medium"
        })
        
        body_items.append({
            "type": "FactSet",
            "facts": schedule_facts,
            "spacing": "Small"
        })

    # ---- Botões de Ação ----
    actions = []
    if official_link:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "🌐 ACESSAR SITE OFICIAL",
            "url": official_link
        })
        
    actions.append({
        "type": "Action.OpenUrl",
        "title": "📋 VER NO EDITAL TRACKER",
        "url": TRACKER_URL
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
                    "body": body_items,
                    "actions": actions
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Notification sent to Teams for {institution}")
        return True
    except Exception as e:
        logger.error(f"Error sending Teams notification: {e}")
        return False