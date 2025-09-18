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
        
        @self.router.get('/get', tags=['Books'])
        def get_book(response: Response, user: Annotated[str, Depends(services.get_current_user)], id: int) -> dict[str, object]:
            book = services.get_book(id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': book.serialize()
                }
            )
        
        @self.router.get('/all', tags=['Books'])
        def get_all_books(response: Response, user: Annotated[str, Depends(services.get_current_user)]) -> dict[str, object]:
            books = services.get_all_books()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': [book.serialize() for book in books]
                }
            )
        
        @self.router.delete('/delete', tags=['Books'])
        def delete_book(response: Response, user: Annotated[str, Depends(services.get_current_user)], id: int) -> dict[str, object]:
            book = services.get_book(id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            services.delete_book(book.id)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
            )

        @self.router.post('/upload', tags=['Books'])
        def upload_book(response: Response, user: Annotated[str, Depends(services.get_current_user)], file: UploadFile = File(...)) -> dict[str, object]:
            book = services.save_book(file, user) # Guarda el libro, valida su formato y más.

            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': book.serialize()
                }
            )