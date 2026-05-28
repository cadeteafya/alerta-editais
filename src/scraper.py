import logging
import requests
from lxml import html
from typing import List, Dict

logger = logging.getLogger(__name__)

TRACKER_URL = "https://edital-tracker-woad.vercel.app/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_articles() -> List[Dict]:
    """Coleta os editais estruturados diretamente da página do Edital Tracker."""
    articles = []
    
    try:
        logger.info(f"Fetching editais from tracker: {TRACKER_URL}")
        response = requests.get(TRACKER_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        tree = html.fromstring(response.content)
        cards = tree.xpath("//article")
        logger.info(f"Found {len(cards)} editais on the page.")
        
        for card in cards:
            # 1. Título
            title_node = card.xpath(".//h3/text()")
            title = title_node[0].strip() if title_node else "Edital sem título"
            
            # 2. Instituição (Acrônimo no banner)
            inst_node = card.xpath(".//div[contains(@style, 'linear-gradient')]//p[contains(@class, 'text-white')]/text()")
            institution = inst_node[0].strip() if inst_node else "Outros"
            
            # 3. Ano
            year_node = card.xpath(".//span[contains(@class, 'font-mono') and contains(@class, 'text-white')]/text()")
            year = year_node[0].strip() if year_node else "2026"
            
            # 4. Tag de Status (ex: "Saiu o edital")
            tag_node = card.xpath(".//span[contains(@class, 'tracking-wider')]/text()")
            tag = tag_node[0].strip() if tag_node else ""
            
            # 5. Data de Publicação (limpa de comments/prefixos)
            pub_node = card.xpath(".//header/p/span//text()")
            pub_date = "".join(pub_node).replace("publicado em", "").strip() if pub_node else "Data não informada"
            
            # 6. Próximo Marco
            next_milestone_node = card.xpath(".//div[contains(@class, 'bg-[var(--surface-muted)]')]//p[contains(@class, 'text-sm') and contains(@class, 'font-medium')]/text()")
            next_milestone = next_milestone_node[0].strip() if next_milestone_node else ""
            
            next_date_node = card.xpath(".//div[contains(@class, 'bg-[var(--surface-muted)]')]//p[contains(@class, 'font-mono')]/text()")
            next_date = next_date_node[0].strip() if next_date_node else ""
            
            next_time_node = card.xpath(".//div[contains(@class, 'bg-[var(--surface-muted)]')]//p[contains(@class, 'text-[11px]')]/text()")
            next_time = next_time_node[0].strip() if next_time_node else ""
            
            # 7. Cronograma Completo
            schedule_items = []
            for li in card.xpath(".//ol/li"):
                stage_node = li.xpath("./span[1]/text()")
                stage = stage_node[0].strip() if stage_node else ""
                
                date_node = li.xpath("./span[2]/text()")
                date = date_node[0].strip() if date_node else ""
                
                if stage and date:
                    schedule_items.append({"stage": stage, "date": date})
            
            # 8. Link Oficial
            link_node = card.xpath(".//a[contains(text(), 'Site oficial')]/@href")
            official_link = link_node[0].strip() if link_node else None
            
            # Chave única para controle de novidades (Título + Data de Publicação)
            unique_key = f"{title} | {pub_date}"
            
            articles.append({
                "title": title,
                "institution": institution,
                "year": year,
                "tag": tag,
                "published_at": pub_date,
                "next_milestone": {
                    "stage": next_milestone,
                    "date": next_date,
                    "time_left": next_time
                },
                "schedule": schedule_items,
                "official_link": official_link,
                "link": unique_key
            })
            
    except Exception as e:
        logger.error(f"Erro ao coletar os editais em {TRACKER_URL}: {e}")
            
    return articles
