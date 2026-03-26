import os
import json
import logging
from google import genai

logger = logging.getLogger(__name__)

def check_if_edital(title: str, paragraph: str) -> dict:
    """Uses the latest Google GenAI SDK to filter for editais."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set.")
        return {"is_edital": False}
        
    client = genai.Client(api_key=api_key)
    # Using gemini-2.5-flash-lite since it has a 1000 requests/day free tier limit (unlike the 20/day of 2.5-flash)
    model_id = 'gemini-2.5-flash-lite'
    
    prompt = f"""
    Analise o título e o resumo abaixo de um artigo do portal Estratégia MED.
    Determine se é um anúncio de NOVO edital sobre:
    1. Residência Médica (incluindo vagas remanescentes/complementares)
    2. Exames de Revalidação de Diplomas (ex: Revalida INEP)
    3. Grandes Concursos na Área Médica Institucionais (ex: Ebserh, Forças Armadas)

    Se for QUALQUER UM desses 3 casos, considere como é um edital válido para os médicos (is_edital: true).

    Responda APENAS com JSON válido. Não inclua markdown, ```json ou outro texto extra.
    Formato esperado:
    {{"is_edital": true, "instituicao": "nome da instituição/exame", "tipo": "Novo Edital de Residência ou Revalidação"}}
    
    Título: {title}
    Resumo: {paragraph}
    """
    
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        # Using simple replace to ensure the response can be parsed
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data
    except Exception as e:
        logger.error(f"Error calling Gemini ({model_id}): {e}")
        # Secondary attempt with a different model if the main choice fails
        try:
             response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
             text = response.text.replace("```json", "").replace("```", "").strip()
             return json.loads(text)
        except:
             return {"is_edital": False}
