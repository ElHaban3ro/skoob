import os
from google import genai
from dotenv import load_dotenv
from google.genai import types

class SearchServices:
    def __init__(self) -> None:
        """Métodos para buscar contenido en internet.
        """
        load_dotenv()

    def gemini_client(self) -> genai.Client:
        """Create a Gemini client.

        Returns:
            dict: Return the Gemini client.
        """
        self.gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY', '')
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        return self.gemini_client

    def setup_gemini_grounded(self) -> types.GenerationConfig:
        """Configura la solicitud para Gemini Grounded Search.
        """
        # We define the grounding type.
        grounding_type = types.Tool(
            google_search=types.GoogleSearch()
        )

        # Configure genetarion settings.
        config = types.GenerateContentConfig(
            tools=[grounding_type],
        )
        return config
    
    def search_with_gemini(self, prompt: str, model: str = 'gemini-2.5-flash-lite') -> str:
        """Realiza una búsqueda utilizando Gemini Grounded Search.

        Args:
            prompt (str): El prompt de búsqueda.

        Returns:
            str: El resultado de la búsqueda.
        """
        gemini_client = self.gemini_client()
        gemini_configs = self.setup_gemini_grounded()
        response = gemini_client.models.generate_content(
            model=model,
            contents=[prompt],
            config=gemini_configs
        )
        return response.text