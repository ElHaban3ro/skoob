from typing import Optional
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from src.models.users_model import UsersModel

class UsersServices:
    def __init__(self) -> None:
        super().__init__()
        self.engine: Engine = self.engine
    
    def get_all_users(self) -> list[UsersModel]:
        with Session(self.engine) as session:
            return session.query(UsersModel).all()

    def user_exist(self, email: str) -> bool:
        with Session(self.engine) as session:
            return True if session.query(UsersModel).filter(UsersModel.email == email).first() else False

    def create_admin_user(self, name: str, email: str, user_type: str = 'google', image: Optional[str] = None) -> UsersModel:
        with Session(self.engine) as session:
            new_user = UsersModel(
                name=name,
                email=email,
                image=image,
                user_type=user_type,
                role='admin'
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user
        
    def create_user(self, name: str, email: str, image: str, type: str = 'google') -> UsersModel:
        with Session(self.engine) as session:
            new_user = UsersModel(
                name=name,
                email=email,
                image=image,
                type=type,
                role='user'
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user