import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def check_if_edital(title: str, paragraph: str) -> dict:
    """Uses Gemini to check if it's a new edital."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return {"is_edital": False}
        
    genai.configure(api_key=api_key)
    # Using the stable model name
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Analise o título e o resumo abaixo de um artigo do portal Estratégia MED.
    Determine se é um anúncio de NOVO edital de residência médica
    (incluindo editais de vagas remanescentes/complementares).

    Responda APENAS com JSON válido. Não inclua markdown, código ou outro texto extra.
    Formato esperado:
    {{"is_edital": true, "instituicao": "nome da instituição", "tipo": "Novo Edital"}}
    
    Título: {title}
    Resumo: {paragraph}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return {"is_edital": False}
