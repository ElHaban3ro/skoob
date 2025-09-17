from fastapi import status
from fastapi.responses import Response

class HttpResponses:
    def __init__(self) -> None:
        pass

    @staticmethod
    def standard_response(response: Response, status_code: status, status_title: str, content_response: object = {}) -> dict[str, object]:
        """Crea una respuesta estandarizada para las respuestas HTTP.

        Args:
            status_code (status): Código de estado HTTP.
            title (str): Título de la respuesta.
            content_response (Object): Contenido de la respuesta.

        Returns:
            dict[str, object]: Diccionario con la respuesta estandarizada.
        """
        response.status_code = status_code
        return {
            'status_title': status_title,
            'content': content_response
        }