from sqlalchemy import Column, Integer, String, ARRAY, ForeignKey
from src.db.declarative_base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
class BooksModel(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, index=True)

    # TODO: Relación con el usuario.

    # Books Data
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    author = Column(String, nullable=True)
    contributor = Column(String, nullable=True)
    category = Column(String, nullable=True)
    publish_date = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    language = Column(String, nullable=True)
    cover_path = Column(String, nullable=True)

    # Paths
    main_folder_path = Column(String, nullable=False)
    original_file_path = Column(String, nullable=False)
    opf_path = Column(String, nullable=False)
    metadata_path = Column(String, nullable=False)
    toc_path = Column(String, nullable=True)

    book_type = Column(String, nullable=False)  # epub, pdf.
    book_content = Column(ARRAY(String), nullable=True)  # List of paths to the book's content files.
    toc_content = Column(JSONB, nullable=True)  # Table of contents structure.

    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('UsersModel', back_populates='books')


    def serialize(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'author': self.author,
            'cover_path': self.cover_path,
            'contributor': self.contributor,
            'category': self.category,
            'publish_date': self.publish_date,
            'publisher': self.publisher,
            'language': self.language,
            'opf_path': self.opf_path,
            'metadata_path': self.metadata_path,
            'toc_path': self.toc_path,
            'book_type': self.book_type,
            'book_content': self.book_content,
            'book_charapters': len(self.book_content) if self.book_content else 0,
            'toc_content': self.toc_content,
            'main_folder_path': self.main_folder_path,
            'original_file_path': self.original_file_path,
            'owner_id': self.owner_id,  
        }