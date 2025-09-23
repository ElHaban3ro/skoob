from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import Response, FileResponse
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from pathlib import Path

from typing import Annotated
from fastapi.security import OAuth2PasswordBearer

class UtilsRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/utils'
        self.router: APIRouter = APIRouter()
        self.search_types = ['definition', 'free']

        @self.router.get('/search', tags=['utils'])
        def google_search(response: Response, search: str, _type: str = 'definition', user = Depends(services.get_current_user)) -> dict[str, object]:
            """Hace una búsqueda en Google utilizando Gemini Grounded Search.

            Args:
                response (Response): _description_
                search (str): Búsqueda a realizar.
                type (str, optional): Tipo de búsqueda. Puede ser de tipo 'definition' o 'free'. Defaults to 'definition'.

            Returns:
                dict[str, object]: devuelve el resultado de la búsqueda.
            """
            if _type not in self.search_types:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status_title='Search type not allowed',
                    content_response={}
                )

            search = services.search_with_gemini(search, search_type=_type)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Search completed',
                content_response={
                    'search_result': search
                }
            )