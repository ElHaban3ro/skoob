from fastapi import APIRouter, status, Depends
from fastapi.responses import Response
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from src.models.users_model import UsersModel

from typing import Annotated, Union
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

class UsersRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/users'
        self.router: APIRouter = APIRouter() 
        

        @self.router.get('/me', tags=['Users'])
        def get_me(response: Response, user: Annotated[str, Depends(services.get_current_user)]) -> dict[str, object]:        
            user: UsersModel = user.serialize()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': user
                }
            )
        
        
        @self.router.put('/edit', tags=['Users'])
        def edit_user(
            response: Response,
            current_user: Annotated[UsersModel, Depends(services.get_current_user)],
            name: Union[str, None] = None,
            password: Union[str, None] = None,
            image: Union[str, None] = None
        ) -> dict:
            # Solo puede editarse a sí mismo
            email = current_user.email

            edited_user = services.edit_user(
            email=email,
            name=name,
            password=password,
            image=image
            )
            return HttpResponses.standard_response(
            response=response,
            status_code=status.HTTP_200_OK,
            status_title='Ok',
            content_response={
                'content': edited_user.serialize(return_books=False)
            }
            )
        
        @self.router.post('/auth', tags=['Users'])
        def auth(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> dict[str, object]:
            username = form_data.username.strip().lower()
            password = form_data.password

            token = services.create_user_token_by_username(username)
            if token:
                return {'access_token': token, 'token_type': 'bearer'}

            email_like = username
            if not services.user_exist(email_like):
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='NotFound',
                )

            if not services.user_credentials_are_valid(email_like, password):
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    status_title='Unauthorized',
                )

            token = services.create_user_token(email_like)
            return {'access_token': token, 'token_type': 'bearer'}


        @self.router.get('/all', tags=['Users'])
        def get_all_users(response: Response, user: Annotated[str, Depends(services.get_current_user)]) -> dict[str, object]:
            users = services.get_all_users()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': [user.serialize() for user in users]
                }
            )

        @self.router.post('/register', tags=['Users'])
        def user_register(response: Response, email: str, password: str, name: str) -> dict[str, object]:
            if services.user_exist(email):
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status_title='AlreadyExist',
                )
            
            user = services.create_user(
                name=name,
                email=email,
                password=password,
                user_type='email'
            )
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': user.serialize(return_books=False)
                }
            )