import os
from typing import Annotated, Optional, Union
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session, joinedload
from src.models.users_model import UsersModel
from src.services.microservices.security_services import SecurityServices
import datetime
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/users/auth')

class UsersServices:
    def __init__(self) -> None:
        super().__init__()
        self.engine: Engine = self.engine
        self.JWT_SECRET_KEY: str = self.JWT_SECRET_KEY
    
    def get_all_users(self) -> list[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).options(joinedload(UsersModel.books)).all()
        
    def get_user(self, email: str) -> Optional[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).filter(UsersModel.email == email).options(joinedload(UsersModel.books)).first()
        
    def get_user_by_id(self, user_id: int) -> Optional[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).filter(UsersModel.id == user_id).options(joinedload(UsersModel.books)).first()

    def user_exist(self, email: str) -> bool:
        with Session(self.engine) as session:
            return True if session.query(UsersModel).filter(UsersModel.email == email).options(joinedload(UsersModel.books)).first() else False

    def create_admin_user(self, name: str, email: str, password: str, user_type: str = 'google', image: Optional[str] = None) -> UsersModel:
        with Session(self.engine) as session:
            new_user = UsersModel(
                name=name,
                email=email,
                password=SecurityServices.hash_password(password),
                image=image,
                user_type=user_type,
                role='admin'
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user
        
    def create_user(self, name: str, email: str, image: Optional[str] = None, password: Union[str, None] = None, user_type: str = 'google', google_token: Union[str, None] = None) -> UsersModel:
        with Session(self.engine) as session:
            if password:
                password = SecurityServices.hash_password(password)
            new_user = UsersModel(
                name=name,
                email=email,
                password=password,
                image=image,
                user_type=user_type,
                google_token=google_token,
                role='user'
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user
        
    def user_credentials_are_valid(self, email: str, password: str) -> bool:
        with Session(self.engine) as session:
            user: UsersModel = session.query(UsersModel).filter(UsersModel.email == email).options(joinedload(UsersModel.books)).first()
            if not user:
                return False
            return SecurityServices.verify_password(password, user.password)
        
    def create_user_token(self, email: str, type: str) -> str:
        with Session(self.engine) as session:
            user = session.query(UsersModel).filter(UsersModel.email == email).first()
            if not user:
                return ''

            to_encode = {'sub': user.email, 'type': 'email' if type == 'email' else 'google'}

            # Establecemos una expiración de 30 minutos para el token.
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10)
            to_encode.update({'exp': expire})

            encode_jwt = jwt.encode(to_encode, self.JWT_SECRET_KEY, algorithm='HS256')
            return encode_jwt

    def get_current_user(self, token: Annotated[str, Depends(oauth2_scheme)]):
        """Obtiene el usuario actual a partir del token JWT.

        Args:
            token (Annotated[str, Depends): Token JWT obtenido de la solicitud.

        Returns:
            UserModel: Devuelve el usuario actual.
        """        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, self.JWT_SECRET_KEY, algorithms=['HS256'])
            email = payload.get('sub')
        except InvalidTokenError:
            raise credentials_exception
        
        user = self.get_user(email)
        if user is None:
            raise credentials_exception
        return user

    def delete_user(self, email: str) -> bool:
        with Session(self.engine) as session:
            user = session.query(UsersModel).filter(UsersModel.email == email).options(joinedload(UsersModel.books)).first()
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True
        
    def edit_user(
            self,
            email: str,
            name: Optional[str] = None,
            password: Optional[str] = None,
            image: Optional[str] = None
    ) -> UsersModel:
        with Session(self.engine) as session:
            user = session.query(UsersModel).filter(UsersModel.email == email).options(joinedload(UsersModel.books)).first()
            if name:
                user.name = name
            if password:
                user.password = SecurityServices.hash_password(password)
            if image:
                user.image = image
            session.commit()
            session.refresh(user)
            return user