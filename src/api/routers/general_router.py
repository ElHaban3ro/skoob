from fastapi import APIRouter, status
from fastapi.responses import Response
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses

class GeneralRouter:
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = ''
        self.router: APIRouter = APIRouter() 

        @self.router.get('/', tags=['General'])
        def base(response: Response) -> dict[str, object]:
            all_users = services.get_all_users()
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={
                    'ping': 'pong'
                }
            )