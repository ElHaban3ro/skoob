from fastapi import FastAPI
from src.api.routers.general_router import GeneralRouter
from src.api.routers.users_router import UsersRouter
from src.api.routers.books_router import BooksRouter
import uvicorn
import os
from src.services.core_services import CoreServices
from dotenv import load_dotenv

class FastApi:
    def __init__(self, services: CoreServices) -> None:
        load_dotenv()
        self.app: FastAPI = FastAPI(debug=True)
        #self.app.add_middleware(SessionMiddleware, os.environ.get('GOOGLE_SECRET_KEY', 'KI'))
        self.services = services
        self.add_routers()

    def run(self) -> None:
        print(f'{"=" * 34}\n{"=" * 10} Starting API {"=" * 10}\n{"=" * 34}')
        self.start()

    def add_routers(self) -> None:
        routers = [GeneralRouter, UsersRouter, BooksRouter]
        
        for router in routers:
            router = router(self.services)
            self.app.include_router(router.router, prefix=router.prefix)

    def start(self) -> None:
        uvicorn.run(self.app, host='0.0.0.0', port=3030)