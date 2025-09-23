from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers.general_router import GeneralRouter
from src.api.routers.users_router import UsersRouter
from src.api.routers.books_router import BooksRouter
from src.api.routers.utils_router import UtilsRouter
from src.api.routers.admin_router import AdminRouter
import uvicorn
import os
from src.services.core_services import CoreServices
from dotenv import load_dotenv
from src.db.security.admin_seeds import default_admins_from_env
from contextlib import asynccontextmanager

class FastApi:
    def __init__(self, services: CoreServices) -> None:
        self.origins = [
            "http://localhost",
            "http://localhost:3000",
            "http://0.0.0.0:3000",
            "https://tests.evasoft.app"
        ]
        load_dotenv()
        self.app: FastAPI = FastAPI(debug=True)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        #self.app.add_middleware(SessionMiddleware, os.environ.get('GOOGLE_SECRET_KEY', 'KI'))
        self.services = services
        self.app: FastAPI = FastAPI(debug=True, lifespan=self._lifespan)
        self.add_routers()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        # seed de admins por defecto jeje
        admins = default_admins_from_env()
        if admins:
            result = self.services.sync_admins(admins, update_passwords=False)
            print("[ADMIN SEED]", result)
        yield

    def run(self) -> None:
        print(f'{"=" * 34}\n{"=" * 10} Starting API {"=" * 10}\n{"=" * 34}')
        self.start()

    def add_routers(self) -> None:
        routers = [GeneralRouter, UsersRouter, BooksRouter, UtilsRouter, AdminRouter]
        
        for router in routers:
            router = router(self.services)
            self.app.include_router(router.router, prefix=router.prefix)

    def start(self) -> None:
        uvicorn.run(self.app, host='0.0.0.0', port=3030)
