from fastapi import APIRouter, UploadFile, Depends, Form, File, status
from sqlalchemy.orm import Session
from src.db.db_connection import DbConnection
from src.services.microservices.pdf_services import PDFServices
from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses

class PDFRouter:
    def __init__(self, services: CoreServices):
        self.prefix: str = "/pdfs"
        self.router: APIRouter = APIRouter()
        self.services = services

        def get_session():
            db = DbConnection().SessionLocal()
            try:
                yield db
            finally:
                db.close()

        # Subida
        @self.router.post("/upload", tags=["PDFs"])
        def upload_pdf(
            response,
            file: UploadFile = File(...),
            title: str = Form(...),
            tags: str = Form(""),
            db: Session = Depends(get_session),
        ):
            service = PDFServices(db)
            pdf, url = service.upload_pdf(file, owner_id=1, title=title, tags=tags)  
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"id": pdf.id, "title": pdf.title, "url": url},
            )

        # Listar PDFs del usuario
        @self.router.get("/my", tags=["PDFs"])
        def list_my_pdfs(response, db: Session = Depends(get_session)):
            service = PDFServices(db)
            pdfs = service.get_user_pdfs(owner_id=1)  
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": pdfs},
            )

        # Compartir 
        @self.router.get("/{pdf_id}/share", tags=["PDFs"])
        def share_pdf(response, pdf_id: int, db: Session = Depends(get_session)):
            service = PDFServices(db)
            link = service.share_pdf(pdf_id)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"share_url": link},
            )

        # Notas
        @self.router.post("/{pdf_id}/notes", tags=["PDFs"])
        def add_note(response, pdf_id: int, page: int, text: str, db: Session = Depends(get_session)):
            service = PDFServices(db)
            note = service.add_note(pdf_id, user_id=1, page=page, text=text)  
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"id": note.id, "page": note.page, "text": note.text},
            )

        @self.router.get("/{pdf_id}/notes", tags=["PDFs"])
        def get_notes(response, pdf_id: int, db: Session = Depends(get_session)):
            service = PDFServices(db)
            notes = service.get_notes(pdf_id, user_id=1)  
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={"content": notes},
            )

        # Recomendaciones 
        @self.router.get("/{pdf_id}/recommendations", tags=["PDFs"])
        def get_recommendations(response, pdf_id: int, db: Session = Depends(get_session)):
            service = PDFServices(db)
            recs = service.recommend(pdf_id)
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title="Ok",
                content_response={
                    "content": [{"id": r.id, "title": r.title, "tags": r.tags} for r in recs]
                },
            )
