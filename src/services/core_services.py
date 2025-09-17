import os
from src.services.microservices.users_services import UsersServices
from sqlalchemy import Engine
from dotenv import load_dotenv

class CoreServices(UsersServices):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        load_dotenv()
        self.JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'supersecretkey')