from fastapi import APIRouter, status, Depends, UploadFile, File
from fastapi.responses import Response
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from pathlib import Path

from typing import Annotated

class BooksRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/books'
        self.router: APIRouter = APIRouter() 
        

        @self.router.post('/upload', tags=['Books'])
        def upload_book(response: Response, user: Annotated[str, Depends(services.get_current_user)], file: UploadFile = File(...)) -> dict[str, object]:
            services.save_book(file, user) # Guarda el libro, valida su formato y más.

            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                }
            )