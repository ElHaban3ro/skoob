import os
from src.services.microservices.users_services import UsersServices
from src.services.microservices.books_services import BooksServices
from src.services.microservices.security_services import SecurityServices
from sqlalchemy import Engine
from dotenv import load_dotenv

class CoreServices(UsersServices, BooksServices, SecurityServices):
    def __init__(self, engine: Engine) -> None:
        load_dotenv()
        self.engine = engine
        self.JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'supersecretkey')
        super().__init__()