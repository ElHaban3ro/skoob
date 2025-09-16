from src.services.microservices.users_services import UsersServices
from sqlalchemy import Engine
class CoreServices(UsersServices):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
