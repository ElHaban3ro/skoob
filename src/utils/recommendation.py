from src.models.pdf import PDF
from sqlalchemy.orm import Session

def recommend_pdfs(db: Session, pdf: PDF, limit: int = 5):
    query =db.query(PDF).filter(PDF.id != pdf.id)
    
    if pdf.tags:
        query = query.filter(PDF.tags.ilike(f"%{pdf.tags}%"))
        
    return query.limit(limit).all()