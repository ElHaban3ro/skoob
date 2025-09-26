from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import Response, FileResponse
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from pathlib import Path

from typing import Annotated
from fastapi.security import OAuth2PasswordBearer

class GeneralRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = ''
        self.router: APIRouter = APIRouter() 
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

        @self.router.get('/', tags=['General'])
        def home(response: Response) -> dict[str, object]:
            all_users = services.get_all_users()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'ping': 'pong'
                }
            )