import logging
import requests
from lxml import html
from typing import List, Dict, Optional
import html as python_html

logger = logging.getLogger(__name__)

# URL da API REST do WordPress para capturar os 30 posts mais recentes do banco de dados,
# sem sofrer geoblocking de layout ou esconder os banners de destaque.
API_URL = "https://med.estrategia.com/portal/wp-json/wp/v2/posts?per_page=30"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Cache de parágrafos populado em fetch_articles 
# para responder instantaneamente a fetch_article_paragraph sem novos GETs
_paragraph_cache: Dict[str, str] = {}

def fetch_articles() -> List[Dict]:
    """Coleta a lista de artigos recentes via API JSON."""
    articles = []
    
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        posts = response.json()
        
        for post in posts:
            title_raw = post.get("title", {}).get("rendered", "")
            # O WP as vezes retorna entidades HTML &amp; ou &#8211;, isso limpa elas.
            title = python_html.unescape(title_raw).strip()
            
            link = post.get("link", "")
            date_str = post.get("date", "")
            content_html = post.get("content", {}).get("rendered", "")
            
            # Extrair parágrafo diretamente do conteúdo recebido no JSON
            paragraph = None
            if content_html:
                try:
                    tree = html.fromstring(content_html)
                    for p in tree.xpath('//p'):
                        text = p.text_content().strip()
                        if len(text) > 25:
                            paragraph = text
                            break
                except Exception as parse_err:
                    logger.debug(f"Erro ao parsear HTML do conteúdo {link}: {parse_err}")
            
            if link:
                _paragraph_cache[link] = paragraph
                articles.append({
                    "title": title,
                    "link": link,
                    "date": date_str
                })
                
    except Exception as e:
        logger.error(f"Erro ao buscar os artigos na API {API_URL}: {e}")
            
    return articles

def fetch_article_paragraph(url: str) -> Optional[str]:
    """Retorna o primeiro parágrafo do artigo a partir do cache já hidratado."""
    return _paragraph_cache.get(url)
