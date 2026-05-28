import json
import os
import logging
from scraper import fetch_articles
from notifier import send_teams_notification

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATE_FILE = "data/last_seen.json"

def load_state() -> dict:
    """Carrega o histórico de editais notificados para evitar envios duplicados."""
    if not os.path.exists("data"):
        os.makedirs("data")
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading state file: {e}")
            return {}
    return {}

def save_state(state: dict):
    """Salva o histórico de editais notificados."""
    try:
        if not os.path.exists("data"):
            os.makedirs("data")
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")

def run():
    logger.info("Starting residency monitor (Vercel Edital Tracker mode)...")
    
    seen_links = load_state()
    new_seen_links = dict(seen_links)
    
    # Coleta os editais estruturados do novo portal
    articles = fetch_articles()
    if not articles:
        logger.warning("No editais found or error fetching.")
        return
        
    new_alerts_sent = 0
    
    for article in articles:
        # A chave 'link' já vem formatada do scraper como "Título | DataPublicação"
        link = article["link"]
        
        if link in seen_links:
            continue # Já notificado anteriormente
            
        logger.info(f"New or updated edital found: {article['title']}")
        
        # Envia a notificação rica ao Teams diretamente
        success = send_teams_notification(article)
        if success:
            # Registra no state apenas se o envio for bem-sucedido
            new_seen_links[link] = article["title"]
            new_alerts_sent += 1
            
    # Salva o novo estado consolidado
    if new_alerts_sent > 0:
        save_state(new_seen_links)
        logger.info(f"Monitor run complete. {new_alerts_sent} new alerts sent.")
    else:
        logger.info("Monitor run complete. No new editais found.")

if __name__ == "__main__":
    run()
