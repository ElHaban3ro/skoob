# src/api/routers/admin_router.py
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse
from typing import Annotated, Optional
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from src.models.users_model import UsersModel

class AdminRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = "/admin"
        self.router: APIRouter = APIRouter(prefix=self.prefix, tags=["Admin"])
        self.services = services

        def admin_required(user = Depends(services.get_current_user),) -> UsersModel:
            if not user or user.role != "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            return user

        @self.router.get("/users", tags=["Admin"])
        def list_users(response: Response, _: Annotated[UsersModel, Depends(admin_required)]) -> dict[str, object]:
            users = services.get_all_users()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": [u.serialize() for u in users]},
            )

        @self.router.delete("/users/{user_id:int}", tags=["Admin"])
        def delete_user(response: Response, user_id: int, _: Annotated[UsersModel, Depends(admin_required)]) -> dict[str, object]:
            user_to_delete = services.get_user_by_id(user_id)
            if not user_to_delete:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "NotFound")
            if user_to_delete.role == "admin":
                return HttpResponses.standard_response(response, status.HTTP_400_BAD_REQUEST, "Forbidden")
            services.delete_user(user_to_delete.email)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": f"User {user_to_delete.email} deleted successfully"},
            )

        @self.router.put("/users/ban", tags=["Admin"])
        def ban_user(
            response: Response,
            email: str,
            permanent: bool = True,
            _: Annotated[UsersModel, Depends(admin_required)] = None,
        ) -> dict[str, object]:
            user = services.get_user(email)
            if not user:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "NotFound")
            if user.role == "admin":
                return HttpResponses.standard_response(response, status.HTTP_400_BAD_REQUEST, "Forbidden")
            # Implementación simple: usar role='banned' para ban permanente.
            # Para ban temporal,  podriamos agregar una columna banned_until en UsersModel y lógica en get_current_user idk?
            updated = services.edit_user(email=email, name=None, password=None, image=None)
            updated.role = "banned" if permanent  else "banned"
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": {"email": email, "role": updated.role}},
            )

        @self.router.put("/users/unban", tags=["Admin"])
        def unban_user(
            response: Response,
            email: str,
            new_role: str = "user",
            _: Annotated[UsersModel, Depends(admin_required)] = None,
        ) -> dict[str, object]:
            user = services.get_user(email)
            if not user:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "NotFound")
            if new_role not in ("user", "admin"):
                return HttpResponses.standard_response(response, status.HTTP_400_BAD_REQUEST, "BadRole")
            updated = services.edit_user(email=email, name=None, password=None, image=None)
            updated.role = new_role
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": {"email": email, "role": updated.role}},
            )

        @self.router.get("/books", tags=["Admin"])
        def list_books(response: Response, _: Annotated[UsersModel, Depends(admin_required)]) -> dict[str, object]:
            books = services.get_all_books()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": [b.serialize() for b in books]},
            )

        @self.router.get("/books/{book_id:int}", tags=["Admin"])
        def get_book(
            response: Response,
            book_id: int,
            _: Annotated[UsersModel, Depends(admin_required)],
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "BookNotFound")
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": book.serialize()},
            )

        @self.router.delete("/books/{book_id:int}", tags=["Admin"])
        def delete_book(
            response: Response,
            book_id: int,
            _: Annotated[UsersModel, Depends(admin_required)],
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "BookNotFound")
            services.delete_book(book.id)
            return HttpResponses.standard_response(response, status.HTTP_200_OK, "Ok")

        @self.router.post("/books/upload", tags=["Admin"])
        def upload_book_for_user(
            response: Response,
            owner_email: str,
            file: UploadFile = File(...),
            admin: Annotated[UsersModel, Depends(admin_required)] = None,
        ) -> dict[str, object]:
            owner = services.get_user(owner_email)
            if not owner:
                return HttpResponses.standard_response(response, status.HTTP_404_NOT_FOUND, "UserNotFound")
            book = services.save_book(file, owner)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": book.serialize()},
            )
