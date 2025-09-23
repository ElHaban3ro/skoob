import httpx
import os
from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import Response, RedirectResponse
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses
from src.models.users_model import UsersModel
from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Annotated, Union
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

class UsersRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/users'
        self.router: APIRouter = APIRouter() 
        GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        GOOGLE_SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY")
        GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_CALLBACK_URI", "http://localhost:3030/users/auth/google/callback")
        GOOGLE_REDIRECT_FRONTEND_URI = os.getenv("GOOGLE_REDIRECT_FRONTEND_URI", "http://localhost:3000")
        GOOGLE_TOKEN_REQUEST_URL = "https://oauth2.googleapis.com/token"

        @self.router.get('/me', tags=['Users'])
        def get_me(response: Response, user = Depends(services.get_current_user)) -> dict[str, object]:        
            user: UsersModel = user.serialize()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': user
                }
            )
        
        @self.router.delete('/delete', tags=['Users'])
        def delete_user(response: Response, user_id: int, user = Depends(services.get_current_user)) -> dict[str, object]:
            user_to_delete = services.get_user_by_id(user_id)
            if not user_to_delete or user.role != 'admin' or user.email == user_to_delete.email:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status_title='Forbidden',
                )
            services.delete_user(user_to_delete.email)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': f'User {user_to_delete.email} deleted successfully'
                }
            )
        
        @self.router.put('/edit', tags=['Users'])
        def edit_user(
            response: Response,
            email: str,
            name: Union[str, None] = None,
            password: Union[str, None] = None,
            image: Union[str, None] = None,
            user = Depends(services.get_current_user),
        ) -> dict:
            # Solo puede editarse a sí mismo
            email = email
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
            
            token = services.create_user_token(email_like, 'email')
            response.delete_cookie(
                key="access_token",
                httponly=True,
                secure=False, # Require HTTP.
                samesite='none', # Accept different site requests.
            )
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=False, # Require HTTP.
                samesite='none', # Accept different site requests.
                max_age=60*180 # 3 hours
            )

            response.status_code = status.HTTP_200_OK
            return {'status': 'logged'}

        @self.router.get('/auth/google', tags=['Users'])
        def google_auth(response: Response) -> dict[str, object]:
            google_auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&response_type=code&scope=openid email profile"
            return RedirectResponse(google_auth_url)

        @self.router.get('/auth/google/callback', tags=['Users'])
        async def google_auth_callback(response: Response, request: Request, code: str) -> dict[str, object]:
            """Receives the callback from Google OAuth2 and processes the authentication.

            Args:
                code (str): Authorization code from Google
            """
            data = {
                'code': code,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_SECRET_KEY,
                'redirect_uri': GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(GOOGLE_TOKEN_REQUEST_URL, data=data)
                response.raise_for_status()
                token_response = response.json()
            
            google_token = token_response.get('id_token')
            if not google_token:
                return RedirectResponse(f'{GOOGLE_REDIRECT_FRONTEND_URI}/login?error=google_auth_failed')
            
            try:
                id_info = id_token.verify_oauth2_token(google_token, requests.Request(), GOOGLE_CLIENT_ID)

                user = services.get_user(id_info['email'])
                if not user:
                    user = services.create_user(
                        name=id_info.get('name'),
                        email=id_info.get('email'),
                        google_token=google_token,
                        image=id_info.get('picture'),
                        user_type='google',
                    )
                else:
                    if user.user_type != 'google':
                        return RedirectResponse(f'{GOOGLE_REDIRECT_FRONTEND_URI}/login?error=user_registred_with_different_method')
                
                local_token = services.create_user_token(user.email, 'google')
                resp = RedirectResponse(f'{GOOGLE_REDIRECT_FRONTEND_URI}/')
                resp.set_cookie(
                    key="access_token",
                    value=local_token,
                    httponly=True,
                    secure=False, # Require HTTP.
                    samesite='none', # Accept different site requests.
                    max_age=60*180 # 3 hours
                )
                return resp

            except ValueError as e:
                return RedirectResponse(f'{GOOGLE_REDIRECT_FRONTEND_URI}/login?error=google_auth_failed')
            except Exception as e:
                return RedirectResponse(f'{GOOGLE_REDIRECT_FRONTEND_URI}/login?error=google_auth_failed')


        @self.router.get('/all', tags=['Users'])
        def get_all_users(response: Response, user = Depends(services.get_current_user)) -> dict[str, object]:
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
        
        @self.router.post('/logout', tags=['Users'])
        def logout_user(response: Response) -> dict[str, object]:
            response.delete_cookie(
                key="access_token",
                httponly=True,
                secure=False, # Require HTTP.
                samesite='none', # Accept different site requests.
            )
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'content': 'Logged out successfully'
                }
            )