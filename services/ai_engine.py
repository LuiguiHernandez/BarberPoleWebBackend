from google import genai
from google.genai import types
from core.config import settings

class CarlosEngine:
    def __init__(self):
        # Inicializamos el cliente principal
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = 'gemini-1.5-flash'

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
        
        try:
            # Usamos client.aio para llamadas asíncronas
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            print(f"Error en CarlosEngine: {e}")
            return "Lo siento, tuve un problema procesando tu mensaje."