import os
from google import genai
from dotenv import load_dotenv
from google.genai import types
from typing import TypedDict

class SearchType(TypedDict):
    raw_text: str
    text_with_citations: str
    citations: dict[str, dict[str, str]]

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
        gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY', '')
        _gemini_client_ = genai.Client(api_key=gemini_api_key)
        return _gemini_client_

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
    
    def search_with_gemini(self, prompt: str, model: str = 'gemini-2.5-flash-lite', search_type: str = 'definition') -> SearchType:
        """Realiza una búsqueda utilizando Gemini Grounded Search.

        Args:
            prompt (str): El prompt de búsqueda.
            model (str, optional): El modelo de Gemini a utilizar. Defaults to 'gemini-2.5-flash-lite'.
            search_type (str, optional): El tipo de búsqueda a realizar. Puede ser 'definition' o 'free'. Este parámetro de utilizará para moldear el prompt desde el front. Defaults to 'definition'.

        Returns:
            str: El resultado de la búsqueda.
        """
        gemini_client = self.gemini_client() # Seteamos el cliente de Gemini.
        gemini_configs = self.setup_gemini_grounded() # Configuramos Gemini Grounded Search.
        response = gemini_client.models.generate_content( # Hacemos la búsqueda.
            model=model,
            #! DANTE, modificá tu promt acá!
            contents=[f'Realiza una búsqueda en Google y responde de forma concisa y clara para definir lo necesario. Responde en el idioma del prompt. Sé corto y conciso. Búsqueda: {prompt}' if search_type == 'definition' else f'Realiza una búsqueda en Google y responde de forma creativa y detallada. Utiliza citas numeradas para referenciar las fuentes de información. Sé corto y conciso. Responde en el idioma del prompt.\n\nBúsqueda: {prompt}'],
            config=gemini_configs
        )
        # Extraemos los resultados y las citas.
        search_supports = response.candidates[0].grounding_metadata.grounding_supports
        # Extraemos los chunks de búsqueda, indican donde comienzan terminan las citas.
        search_chunks = response.candidates[0].grounding_metadata.grounding_chunks
        sorted_supports = sorted(search_supports, key=lambda s: s.segment.end_index, reverse=True)
        citation_links = {}
        response_text = response.text

        for support in sorted_supports:
            end_index = support.segment.end_index
            if support.grounding_chunk_indices: # Si hay citas.
                citation_links_list = []
                for i in support.grounding_chunk_indices: # Recorremos los índices de los chunks.
                    if i < len(search_chunks): # Verificamos que el índice esté dentro del rango.
                        uri = search_chunks[i].web.uri # Extraemos el URI.
                        citation_links[i] = { # Generamos el diccionario de citas.
                            'uri': uri,
                            'from': search_chunks[i].web.title
                        }
                        citation_links_list.append(f"<reference>[{i + 1}]({uri})<reference/>") # Formateamos la cita, para ser añadida en el texto.
                citation_string = ', '.join(citation_links_list)
                response_text = response_text[:end_index] + citation_string + response_text[end_index:]
        
        formated_response = {
            'raw_text': response.text,
            'text_with_citations': response_text,
            'citations': citation_links
        }

        return formated_response