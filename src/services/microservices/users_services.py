import os
from typing import Annotated, Optional, Union
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer, APIKeyCookie
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

    def _norm_email(self, email: str) -> str:
        return (email or "").strip().lower()
    
    def _norm_username(self, username: str) -> str:
        return (username or "").strip().lower()

    def get_admin_env_index(self) -> dict:
        from src.db.security.admin_seeds import admin_env_index
        return admin_env_index()

    def ensure_admin_from_username(self, username: str) -> UsersModel | None:
        # Normalizamos el username para evitar problemas de mayúsculas/minúsculas y espacios
        # buscamos en el índice de admins cargados desde variables de entorno
        username = self._norm_username(username)
        idx = self.get_admin_env_index()
        admin_data = idx.get(username)
        if not admin_data:
            return None
        email = self._norm_email(admin_data["email"])
        name = admin_data["name"]
        password = admin_data["password"]
        self.create_admin_user_if_missing(name=name, email=email, password=password)
        return self.get_user(email)


    def get_all_users(self) -> list[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).options(joinedload(UsersModel.books)).all()
        
    def get_user(self, email: str) -> Optional[UsersModel]:
        # Normalizamos el email para evitar problemas de mayúsculas/minúsculas y espacios
        email = self._norm_email(email)
        with Session(self.engine) as session:
            return (
                session.query(UsersModel)
                .filter(UsersModel.email.ilike(email))
                .options(joinedload(UsersModel.books))
                .first()
            )
            
    def get_user_by_id(self, user_id: int) -> Optional[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).filter(UsersModel.id == user_id).options(joinedload(UsersModel.books)).first()

    def user_exist(self, email: str) -> bool:
        email = self._norm_email(email)
        with Session(self.engine) as session:
            return bool(
                session.query(UsersModel)
                .filter(UsersModel.email.ilike(email))
                .options(joinedload(UsersModel.books))
                .first()
            )

    def create_admin_user_if_missing(self, name: str, email: str, password: str) -> bool:
        email = self._norm_email(email)
        with Session(self.engine) as session:
            exists = session.query(UsersModel).filter(UsersModel.email.ilike(email)).first()
            if exists:
                if exists.role != "admin":
                    exists.role = "admin"
                    if password:
                        exists.password = SecurityServices.hash_password(password)
                    session.commit()
                return False
            new_user = UsersModel(
                name=name,
                email=email,
                password=SecurityServices.hash_password(password),
                image=None,
                user_type="email",
                role="admin",
            )
            session.add(new_user)
            session.commit()
            return True

    def seed_admins(self, admins: list[dict]) -> dict:
        # hace seed de admins y devuelve los creados y los que ya existian 
        created, skipped = [], []
        for a in admins:
            ok = self.create_admin_user_if_missing(a["name"], a["email"], a["password"])
            if ok:
                created.append(a["email"])
            else:
                skipped.append(a["email"])
        return {"created": created, "skipped": skipped}

    def create_admin_user(self, name: str, email: str, password: str, user_type: str = 'email', image: Optional[str] = None) -> UsersModel:
        self.create_admin_user_if_missing(name, email, password)
        with Session(self.engine) as session:
            return session.query(UsersModel).filter(UsersModel.email == email).first()
   
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
        email = self._norm_email(email)
        with Session(self.engine) as session:
            user = (
                session.query(UsersModel)
                .filter(UsersModel.email.ilike(email))
                .options(joinedload(UsersModel.books))
                .first()
            )
            if not user:
                return False
            return SecurityServices.verify_password(password, user.password)
        
    def create_user_token(self, email: str, type: str) -> str:
        email = self._norm_email(email)
        with Session(self.engine) as session:
            user = session.query(UsersModel).filter(UsersModel.email.ilike(email)).first()
            if not user:
                return ''

            to_encode = {'sub': user.email, 'type': 'email' if type == 'email' else 'google'}

            # Establecemos una expiración de 30 minutos para el token.
            expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10)
            to_encode.update({'exp': expire})

            encode_jwt = jwt.encode(to_encode, self.JWT_SECRET_KEY, algorithm='HS256')
            return encode_jwt
        
    def get_current_user(self, response: Response, request: Request):
        """Obtiene el usuario actual a partir del token JWT.

        Args:
            token (Annotated[str, Depends): Token JWT obtenido de la solicitud.

        Returns:
            UserModel: Devuelve el usuario actual.
        """        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        
        key = request.cookies.get("access_token")

        try:
            payload = jwt.decode(key, self.JWT_SECRET_KEY, algorithms=['HS256'])
            email = payload.get('sub')
        except InvalidTokenError:
            raise credentials_exception
        
        user = self.get_user(email)
        if user is None:
            raise credentials_exception
        return user

    def delete_user(self, email: str) -> bool:
        email = self._norm_email(email)
        with Session(self.engine) as session:
            user = (
                session.query(UsersModel)
                .filter(UsersModel.email.ilike(email))
                .options(joinedload(UsersModel.books))
                .first()
            )
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
        image: Optional[str] = None,
    ) -> UsersModel:
        email = self._norm_email(email)
        with Session(self.engine) as session:
            user = (
                session.query(UsersModel)
                .filter(UsersModel.email.ilike(email))
                .options(joinedload(UsersModel.books))
                .first()
            )
            if name:
                user.name = name
            if password:
                user.password = SecurityServices.hash_password(password)
            if image:
                user.image = image
            session.commit()
            session.refresh(user)
            return user
        
    def sync_admins(self, admins: list[dict], update_passwords: bool = False) -> dict:
        created, updated = [], []
        with Session(self.engine) as session:
            for a in admins:
                email = self._norm_email(a["email"])
                user = session.query(UsersModel).filter(UsersModel.email.ilike(email)).first()
                if user:
                    user.role = "admin"
                    if update_passwords:
                        user.password = SecurityServices.hash_password(a["password"])
                    session.commit()
                    updated.append(email)
                else:
                    new_user = UsersModel(
                        name=a["name"],
                        email=email,
                        password=SecurityServices.hash_password(a["password"]),
                        image=None,
                        user_type="email",
                        role="admin",
                    )
                    session.add(new_user)
                    session.commit()
                    created.append(email)
        return {"created": created, "updated": updated}