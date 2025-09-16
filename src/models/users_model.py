from sqlalchemy import Column, Integer, String
from src.db.declarative_base import Base

class UserModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    image = Column(String, nullable=False)
    type = Column(String, default='google')  # e.g., 'google', 'x', 'facebook'.