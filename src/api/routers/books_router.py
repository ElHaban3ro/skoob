import mimetypes
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import Response, FileResponse
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from pathlib import Path, PurePosixPath

from typing import Annotated

class BooksRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/books'
        self.router: APIRouter = APIRouter() 
        def raise_authorized() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You don't have permission to perform this action"
            )
        
        @self.router.get('/content/{book_id:int}/{path_fragments:path}', tags=['Books'])
        def book_content_resolve(response: Response, book_id: int, path_fragments: str, user = Depends(services.get_current_user)) -> FileResponse:
            """Resuelve y sirve archivos estáticos relacionados con los libros, como imágenes o estilos CSS.

            Args:
                path_fragments (str): Fragmentos de la ruta del archivo solicitado.
            """
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            # Solo el usuario puede acceder a su propio recurso.
            if book.owner_id != user.id:
                return raise_authorized()
            
            resource_relative_path = PurePosixPath(path_fragments)  # Normaliza la ruta para evitar problemas de seguridad
            resource_path = (Path(book.opf_path).parent.resolve() / resource_relative_path).resolve()
            if resource_relative_path.is_absolute() or any(part == '..' for part in resource_relative_path.parts) or str(Path(book.opf_path).parent) not in str(resource_path):
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status_title='SuckMyDickBruh',
                )

            if not resource_path.exists() or not resource_path.is_file():
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='ResourceNotFound',
                )
            return FileResponse(path=resource_path, media_type=mimetypes.guess_type(resource_path)[0])

        @self.router.get('/get/cover', tags=['Books'])
        def get_book_cover(response: Response, book_id: int, user = Depends(services.get_current_user)) -> FileResponse:
            """Obtiene la portada de un libro.

            Args:
                book_id (int): Id del libro.

            Returns:
                FileResponse: Devuelve la imagen de la portada del libro.
            """            
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            if not book.cover_path or not Path(book.cover_path).exists():
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='CoverNotFound',
                )
            
            if book.owner_id != user.id:
                return raise_authorized()

            mediatype, _ = mimetypes.guess_type(book.cover_path)
            return FileResponse(path=Path(book.cover_path), media_type=mediatype)

        @self.router.get('/read', tags=['Books'])
        def read_book(response: Response, book_id: int, chapter_number: int, user = Depends(services.get_current_user)) -> FileResponse:
            """Obtiene el contenido HTML de un capítulo específico de un libro.

            Args:
                book_id (int): Id del libro.
                chapter_number (int): Número del capítulo a leer.

            Returns:
                HTMLResponse: Devuelve el contenido HTML del capítulo solicitado.
            """            
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            if book.owner_id != user.id:
                return raise_authorized()

            chapter_path = services.read_book(book_id, chapter_number)
            mediatype, _ = mimetypes.guess_type(chapter_path)
            return FileResponse(path=Path(chapter_path), media_type=mediatype)

        @self.router.get('/get', tags=['Books'])
        def get_book(response: Response, id: int, user = Depends(services.get_current_user)) -> dict[str, object]:
            book = services.get_book(id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                return raise_authorized()
            
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': book.serialize()
                }
            )
        
        @self.router.get('/all', tags=['Books'])
        def get_all_books(response: Response, user = Depends(services.get_current_user)) -> dict[str, object]:
            """Devuelve los libros del usuario autenticado."""
            books = services.get_all_my_books(user)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': [book.serialize() for book in books]
                }
            )
        
        @self.router.delete('/delete', tags=['Books'])
        def delete_book(response: Response, id: int, user = Depends(services.get_current_user)) -> dict[str, object]:
            book = services.get_book(id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                return raise_authorized()
            
            services.delete_book(book.id)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
            )

        @self.router.post('/upload', tags=['Books'])
        def upload_book(response: Response, user = Depends(services.get_current_user), file: UploadFile = File(...)) -> dict[str, object]:
            book = services.save_book(file, user) # Guarda el libro, valida su formato y más.

            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': book.serialize()
                }
            )