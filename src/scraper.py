import logging
import requests
from lxml import html
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Monitoramos as categorias diretamente porque a Home Page pura (/) 
# entrega um layout capado para os IPs americanos do GitHub Actions.
TARGET_URLS = [
    "https://med.estrategia.com/portal/?s=editais",   # Busca Padrão
    "https://med.estrategia.com/portal/noticias/",    # Notícias (Onde o Revalida INEP foi postado)
    "https://med.estrategia.com/portal/concursos/"    # Aba de grandes Concursos Médicos
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_articles() -> List[Dict]:
    """Coleta a lista de artigos recentes do portal a partir de múltiplas fontes."""
    articles = []
    seen_urls = set()
    
    for url in TARGET_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            tree = html.fromstring(response.content)
            
            # O Estratégia Med usa a tag <article> em ambas as páginas
            for article in tree.xpath('//article'):
                title_node = article.xpath('.//h2//a') or article.xpath('.//h3//a')
                if not title_node:
                    continue
                
                title = title_node[0].text_content().strip()
                link = title_node[0].get('href')
                
                # Evita duplicação se o artigo aparecer nas duas páginas
                if link in seen_urls:
                    continue
                    
                seen_urls.add(link)
                
                date_node = article.xpath('.//time')
                date_str = date_node[0].get('datetime') if date_node else ""
                
                articles.append({
                    "title": title,
                    "link": link,
                    "date": date_str
                })
        except Exception as e:
            logger.error(f"Erro ao buscar os artigos em {url}: {e}")
            
    return articles

def fetch_article_paragraph(url: str) -> Optional[str]:
    """Extrai o primeiro parágrafo significativo de um artigo."""
    try:
        # Adiciona Referer para evitar o 403 Forbidden
        headers = dict(HEADERS)
        headers["Referer"] = "https://med.estrategia.com/portal/"
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        
        # Estratégia #1: Metadados da página (Resumo confiável e não-bloqueado)
        meta_desc = tree.xpath('//meta[@property="og:description" or @name="description"]/@content')
        if meta_desc and len(meta_desc[0].strip()) > 25:
            return meta_desc[0].strip()
            
        # Estratégia #2: Procuramos o primeiro paragrafo que faz sentido no corpo
        selectors = [
            '//div[contains(@class, "entry-content")]//p',
            '//div[contains(@class, "ast-article-single")]//p',
            '//div[contains(@class, "post-content")]//p',
            '//article//p',
            '//body//p'
        ]
        
        for selector in selectors:
            paragraphs = tree.xpath(selector)
            for p in paragraphs:
                text = p.text_content().strip()
                # Pelo menos 25 caracteres para evitar legendas curtas ou botões
                if len(text) > 25:
                    return text
                
        return None
    except Exception as e:
        logger.error(f"Erro ao extrair parágrafo do link {url}: {e}")
        return None
