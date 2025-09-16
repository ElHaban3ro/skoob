# type: ignore
from fastapi import APIRouter

class GeneralRouter:
    def __init__(self) -> None:
        self.prefix: str = ''
        self.router: APIRouter = APIRouter() 

        @self.router.get('/', tags=['General'])
        def ping() -> dict[str, str]:
            return {'ping': 'pong!'}