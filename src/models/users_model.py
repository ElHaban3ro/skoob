import os
from sqlalchemy import Column, Integer, String, ARRAY
from sqlalchemy.orm import relationship
from src.db.declarative_base import Base
from src.models.books_model import BooksModel

class UsersModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=True)  # Nullable for OAuth users.
    google_token = Column(String, nullable=True)  # Store Google OAuth token.
    #tokens = Column(ARRAY(String), default=[])  # Store active tokens.
    image = Column(String, nullable=True)
    user_type = Column(String, default='google')  # e.g., 'google', 'email'.
    role = Column(String, default='user')  # e.g., 'user', 'admin'.

    books = relationship(BooksModel, back_populates='owner', cascade="all, delete-orphan")

    def serialize(self, retireve_password: bool = False, return_books: bool = True) -> dict[str, object]:
        API_URL = os.getenv("API_URL", "http://127.0.0.1:3030")
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'password': self.password if retireve_password else None,
            'image': self.image if self.image else f'{API_URL}/default-avatar',
            'type': self.user_type,
            'role': self.role,
            'books': [book.id for book in self.books] if return_books else []
        }