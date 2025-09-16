from fastapi import FastAPI
from src.api.routers.general_router import GeneralRouter
import uvicorn

class FastApi:
    def __init__(self) -> None:
        self.app: FastAPI = FastAPI(debug=True)
        self.add_routers()

    def run(self) -> None:
        print(f'{"=" * 34}\n{"=" * 10} Starting API {"=" * 10}\n{"=" * 34}')
        self.start()

    def add_routers(self) -> None:
        routers = [GeneralRouter]
        
        for router in routers:
            router = router()
            self.app.include_router(router.router, prefix=router.prefix)

    def start(self) -> None:
        uvicorn.run(self.app, host='0.0.0.0', port=3030)