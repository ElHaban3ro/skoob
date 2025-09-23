import os
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.models.pdf import PDF
from src.models.pdf_note import PDFNote
from src.utils import storage, recommendation

class PDFServices:
    def __init__(self, db: Session):
        self.db = db

    # Subida de PDF
    def upload_pdf(self, file: UploadFile, owner_id: int, title: str, tags: str = ""):
        url = storage.save_file(file.file, file.filename)
        pdf = PDF(title=title, filename=file.filename, owner_id=owner_id, tags=tags)
        self.db.add(pdf)
        self.db.commit()
        self.db.refresh(pdf)
        return pdf, url

    # Obtener PDFs del usuario 
    def get_user_pdfs(self, owner_id: int):
        return self.db.query(PDF).filter(PDF.owner_id == owner_id).all()

    # Compartir 
    def share_pdf(self, pdf_id: int):
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            return None
        return storage.generate_share_link(pdf.filename)

    # Notas personales
    def add_note(self, pdf_id: int, user_id: int, page: int, text: str):
        note = PDFNote(pdf_id=pdf_id, user_id=user_id, page=page, text=text)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_notes(self, pdf_id: int, user_id: int):
        return self.db.query(PDFNote).filter_by(pdf_id=pdf_id, user_id=user_id).all()

    # Recomendaciones 
    def recommend(self, pdf_id: int):
        pdf = self.db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            return []
        return recommendation.recommend_pdfs(self.db, pdf)
