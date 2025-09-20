from fastapi import FastAPI
from src.api.routers.general_router import GeneralRouter
from src.api.routers.users_router import UsersRouter
from src.api.routers.books_router import BooksRouter
from src.api.routers.admin_router import AdminRouter
import uvicorn

from src.services.core_services import CoreServices
from src.db.security.admin_seeds import default_admins_from_env
from contextlib import asynccontextmanager


class FastApi:
    def __init__(self, services: CoreServices) -> None:
        self.services = services
        self.app: FastAPI = FastAPI(debug=True, lifespan=self._lifespan)
        self.add_routers()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        # seed de admins por defecto jeje
        admins = default_admins_from_env()
        if admins:
            result = self.services.sync_admins(admins, update_passwords=True)
            print("[ADMIN SEED]", result)
        yield

    def run(self) -> None:
        print(f'{"=" * 34}\n{"=" * 10} Starting API {"=" * 10}\n{"=" * 34}')
        self.start()

    def add_routers(self) -> None:
        routers = [GeneralRouter, UsersRouter, BooksRouter, AdminRouter]
        for router in routers:
            router = router(self.services)
            self.app.include_router(router.router, prefix=router.prefix)

    def start(self) -> None:
        uvicorn.run(self.app, host='0.0.0.0', port=3030)
