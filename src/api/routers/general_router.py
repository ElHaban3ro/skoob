from fastapi import APIRouter
from src.services.core_services import CoreServices

class GeneralRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = ''
        self.router: APIRouter = APIRouter() 

        @self.router.get('/', tags=['General'])
        def base() -> dict[str, object]:
            all_users = services.get_all_users()
            return {'response': 'what are you doing here? tomátela', 'test': [user.serialize() for user in all_users]}