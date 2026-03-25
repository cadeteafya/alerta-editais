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
    # Using the latest Flash model as requested by user (Flash Lite 2.0)
    # gemini-2.0-flash-lite-preview-02-05 is a reliable lite model name
    model_id = 'gemini-2.0-flash-lite-preview-02-05'
    
    prompt = f"""
    Analise o título e o resumo abaixo de um artigo do portal Estratégia MED.
    Determine se é um anúncio de NOVO edital de residência médica
    (incluindo editais de vagas remanescentes/complementares).

    Responda APENAS com JSON válido. Não inclua markdown, ```json ou outro texto extra.
    Formato esperado:
    {{"is_edital": true, "instituicao": "nome da instituição", "tipo": "Novo Edital"}}
    
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
        # Secondary attempt with a most common model if the user choice fails
        try:
             response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
             text = response.text.replace("```json", "").replace("```", "").strip()
             return json.loads(text)
        except:
             return {"is_edital": False}
