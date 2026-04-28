# services/ai_engine.py
import google.generativeai as genai
from core.config import settings

class CarlosEngine:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def pedir_respuesta(self, prompt_sistema: str, historial: str, mensaje_nuevo: str):
        prompt_final = f"""
        CONTEXTO Y REGLAS:
        {prompt_sistema}

        HISTORIAL DE CONVERSACIÓN:
        {historial}

        MENSAJE DEL CLIENTE:
        {mensaje_nuevo}

        RESPUESTA DE Carlos:
        """
        response = await self.model.generate_content_async(prompt_final)
        return response.text