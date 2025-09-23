from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from src.db.db_connection import Base
import datetime

class PDF(Base):
    __tablename__ = "pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    filename = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_private = Column(Boolean, default=True)
    tags = Column(String)
    
    owner = relationship("UsersModel", back_populates="pdfs") 
    notes = relationship("PDFNote", back_populates="pdf", cascade="all, delete")
