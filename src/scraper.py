import logging
import requests
from lxml import html
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

SEARCH_URL = "https://med.estrategia.com/portal/?s=editais"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_articles() -> List[Dict]:
    """Coleta a lista de artigos recentes do portal."""
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        articles = []
        
        # O Estratégia Med usa a tag <article>
        for article in tree.xpath('//article'):
            title_node = article.xpath('.//h2//a')
            if not title_node:
                continue
            
            title = title_node[0].text_content().strip()
            link = title_node[0].get('href')
            
            date_node = article.xpath('.//time')
            date_str = date_node[0].get('datetime') if date_node else ""
            
            articles.append({
                "title": title,
                "link": link,
                "date": date_str
            })
            
        return articles
    except Exception as e:
        logger.error(f"Erro ao buscar os artigos: {e}")
        return []

def fetch_article_paragraph(url: str) -> Optional[str]:
    """Extrai o primeiro parágrafo significativo de um artigo."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        
        # Procuramos o primeiro paragrafo que faz sentido (sem tags vazias)
        paragraphs = tree.xpath('//div[contains(@class, "entry-content")]//p')
        for p in paragraphs:
            text = p.text_content().strip()
            # Mais de 50 caracteres para evitar legendas curtas ou botões com tag P
            if len(text) > 50:
                return text
                
        # Caso fallback do layout normal caso mude
        for p in tree.xpath('//article//p'):
            text = p.text_content().strip()
            if len(text) > 50:
                return text
                
        return None
    except Exception as e:
        logger.error(f"Erro ao extrair parágrafo do link {url}: {e}")
        return None
