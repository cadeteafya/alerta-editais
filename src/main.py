import json
import os
import logging
from scraper import fetch_articles, fetch_article_paragraph
from ai_filter import check_if_edital
from notifier import send_teams_notification

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATE_FILE = "data/last_seen.json"

def load_state():
    if not os.path.exists("data"):
        os.makedirs("data")
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading state file: {e}")
            return {}
    return {}

def save_state(state):
    try:
        if not os.path.exists("data"):
            os.makedirs("data")
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")

def run():
    logger.info("Starting residency monitor...")
    
    seen_links = load_state()
    new_seen_links = dict(seen_links)
    
    articles = fetch_articles()
    if not articles:
        logger.error("No articles found or error fetching.")
        return
        
    for article in articles:
        link = article["link"]
        if link in seen_links:
            continue # Already processed
            
        logger.info(f"New article found: {article['title']}")
        
        # Add to state to prevent re-processing
        new_seen_links[link] = article["title"]
        
        paragraph = fetch_article_paragraph(link)
        if not paragraph:
            logger.warning(f"Could not extract paragraph for {link}")
            continue
            
        edital_info = check_if_edital(article["title"], paragraph)
        
        if edital_info.get("is_edital"):
            logger.info(f"Confirmed as edital: {edital_info.get('instituicao')}. Sending notification...")
            from scraper import fetch_article_links
            action_links = fetch_article_links(link)
            send_teams_notification(edital_info, paragraph, link, action_links)
        else:
            logger.info("Not an edital.")
            
        # Delay de 15 segundos para evitar erro 429 (Rate Limit de 5 requisições do Gemini Free Tier)
        import time
        time.sleep(15)
            
    save_state(new_seen_links)
    logger.info("Monitor run complete.")

if __name__ == "__main__":
    run()
