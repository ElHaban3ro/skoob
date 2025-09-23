import pprint
from src.api.api import FastApi
from src.db.db_connection import DbConnection
from src.services.core_services import CoreServices

db = DbConnection()
services = CoreServices(db.engine)

api = FastApi(services)
api.run()
