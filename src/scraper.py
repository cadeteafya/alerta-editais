import logging
import requests
from lxml import html
from typing import List, Dict, Optional
import html as python_html
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Base da URL da API REST do WordPress.
# O parâmetro `after` é calculado dinamicamente para uma janela de 30 dias,
# bloqueando artigos históricos de 2023/2024 antes mesmo de chegarem ao last_seen.json.
WP_API_BASE = "https://med.estrategia.com/portal/wp-json/wp/v2/posts"

def _build_api_url() -> str:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{WP_API_BASE}?per_page=20&after={cutoff}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Cache de parágrafos e botões populado em fetch_articles 
# para responder instantaneamente a fetch_article... sem novos GETs
_paragraph_cache: Dict[str, str] = {}
_links_cache: Dict[str, List[Dict]] = {}

def fetch_articles() -> List[Dict]:
    """Coleta a lista de artigos recentes via API JSON."""
    articles = []
    
    try:
        api_url = _build_api_url()
        logger.info(f"Fetching articles from API (cutoff: last 30 days): {api_url}")
        response = requests.get(api_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        posts = response.json()
        
        for post in posts:
            title_raw = post.get("title", {}).get("rendered", "")
            # O WP as vezes retorna entidades HTML &amp; ou &#8211;, isso limpa elas.
            title = python_html.unescape(title_raw).strip()
            
            link = post.get("link", "")
            date_str = post.get("date", "")
            content_html = post.get("content", {}).get("rendered", "")
            
            # Extrair parágrafo e links dinâmicos do HTML recebido no JSON
            paragraph = None
            extracted_links = []
            
            if content_html:
                try:
                    tree = html.fromstring(content_html)
                    # 1. Parágrafo resumo
                    for p in tree.xpath('//p'):
                        text = p.text_content().strip()
                        if len(text) > 25:
                            paragraph = text
                            break
                            
                    # 2. Botões Verdes (PDFs)
                    for a in tree.xpath('//a'):
                        text = (a.text_content() or "").strip().upper()
                        href = a.get('href', '')
                        if ('EDITAL' in text or 'RETIFICAÇÃO' in text) and len(text) < 60 and href:
                            extracted_links.append({'title': text, 'url': href})
                            
                    # 3. Links da Banca (Disclaimer Box)
                    for p in tree.xpath('//p | //div'):
                        p_text = (p.text_content() or "").lower()
                        if 'essencial que o candidato acompanhe' in p_text and 'página oficial' in p_text:
                            for a in p.xpath('.//a'):
                                text = (a.text_content() or "").strip().upper()
                                href = a.get('href', '')
                                if href and text:
                                    extracted_links.append({'title': text, 'url': href})
                            break
                except Exception as parse_err:
                    logger.debug(f"Erro ao parsear HTML do conteúdo {link}: {parse_err}")
            
            if link:
                _paragraph_cache[link] = paragraph
                _links_cache[link] = extracted_links
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

def fetch_article_links(url: str) -> List[Dict]:
    """Retorna os botões dinâmicos (PDFs e Banca) extraídos do artigo."""
    return _links_cache.get(url, [])
