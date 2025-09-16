from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, URL
from src.db.declarative_base import Base

class DbConnection:
    def __init__(self) -> None:
        load_dotenv()
        self.DB_NAME: str = os.getenv('DB_NAME', 'skoob')
        self.DB_USER: str = os.getenv('DB_USER', 'postgres')
        self.DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'password')
        self.DB_HOST: str = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT: int = int(os.getenv('DB_PORT', '5432'))
        self.connect()

    def connect(self) -> None:
        self.engine = create_engine(URL.create(
            drivername='postgresql+psycopg2',
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME
        ))
        Base.metadata.create_all(self.engine)