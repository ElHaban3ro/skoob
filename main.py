import pprint
from src.api.api import FastApi
from src.db.db_connection import DbConnection
from src.services.core_services import CoreServices


db = DbConnection() # Conexión con la base de datos.
services = CoreServices(db.engine) # Servicios.

## TODO: SACAR ESTO
if not services.user_exist('ferdhaban@gmail.com'):
    services.create_admin_user('somaz', 'ferdhaban@gmail.com', 'mypassword', user_type='email')
## TODO: =====================

elhaban3ro_search = services.search_with_gemini('Busca información sobre "ElHaban3ro" en internet. La búsqueda debe ser exclusiva para este tema (incluir comillas para la consulta).')
pprint.pprint(elhaban3ro_search)

api = FastApi(services)
api.run()