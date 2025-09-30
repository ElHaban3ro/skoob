from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, Callable

from fastapi import HTTPException, status
from lxml import html, etree
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from google import genai
from dotenv import load_dotenv

from src.models.books_model import BooksModel


class GeminiServices:
    def __init__(self, engine: Engine, api_key: Optional[str] = None) -> None:
        self.engine = engine
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash-exp"
        
        self.translation_prompt = (
            "Eres un traductor profesional especializado en literatura.\n"
            "Tu tarea es traducir el siguiente contenido HTML de un libro al idioma {target_language}.\n\n"
            "REGLAS IMPORTANTES:\n"
            "1. Mantén TODAS las etiquetas HTML exactamente como están\n"
            "2. Traduce SOLO el texto dentro de las etiquetas, no los atributos\n"
            "3. Preserva los saltos de línea y la estructura del documento\n"
            "4. No agregues explicaciones ni comentarios adicionales\n"
            "5. Devuelve ÚNICAMENTE el HTML traducido\n\n"
            "Contenido a traducir:\n"
            "{content}"
        )

        self.metadata_translation_prompt = (
            "Traduce el siguiente texto al idioma {target_language}.\n"
            "Responde ÚNICAMENTE con la traducción, sin explicaciones adicionales.\n\n"
            "Texto: {text}"
        )
        
        self.summary_prompt = (
            "Eres un analista literario experto.\n"
            "Analiza el siguiente fragmento del libro \"{title}\" y proporciona un resumen conciso pero informativo.\n\n"
            "REGLAS:\n"
            "1. Resume los puntos principales de este fragmento\n"
            "2. Mantén coherencia narrativa\n"
            "3. Sé conciso pero completo\n"
            "4. Máximo 500 palabras por fragmento\n\n"
            "Contenido:\n"
            "{content}"
        )
        
        self.final_summary_prompt = (
            "Eres un analista literario experto.\n"
            "Basándote en los siguientes resúmenes parciales del libro \"{title}\" de {author}, crea un resumen final coherente y completo.\n\n"
            "REGLAS:\n"
            "1. Integra todos los resúmenes parciales en uno cohesivo\n"
            "2. Identifica los temas principales\n"
            "3. Mantén estructura lógica\n"
            "4. Máximo 2000 palabras\n\n"
            "Resúmenes parciales:\n"
            "{partial_summaries}"
        )

    def _extract_text_from_html(self, html_path: str) -> str:
        tree = html.parse(html_path)
        return etree.tostring(tree, encoding='unicode', method='html')

    def _extract_clean_text(self, html_path: str) -> str:
        tree = html.parse(html_path)
        return ' '.join(tree.xpath('//text()'))

    def _chunk_html_content(self, html_content: str, max_chunk_size: int = 30000) -> list[str]:
        if len(html_content) <= max_chunk_size:
            return [html_content]
        
        tree = html.fromstring(html_content)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for element in tree.iter():
            element_str = etree.tostring(element, encoding='unicode')
            element_size = len(element_str)
            
            if current_size + element_size > max_chunk_size and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(element_str)
            current_size += element_size
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        return chunks if chunks else [html_content]

    def _save_progress(self, book_id: int, progress_data: dict, operation: str) -> None:
        progress_dir = Path('./content/progress')
        progress_dir.mkdir(parents=True, exist_ok=True)
        progress_file = progress_dir / f"{operation}_{book_id}.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

    def _load_progress(self, book_id: int, operation: str) -> Optional[dict]:
        progress_file = Path(f'./content/progress/{operation}_{book_id}.json')
        if progress_file.exists():
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _translate_chunk(self, chunk: str, target_language: str) -> str:
        prompt = self.translation_prompt.format(target_language=target_language, content=chunk)
        resp = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return resp.text

    def _translate_text(self, text: str, target_language: str) -> str:
        if not text:
            return text
        prompt = self.metadata_translation_prompt.format(target_language=target_language, text=text)
        resp = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return resp.text.strip()

    def _create_translated_book_structure(self, original_book: BooksModel, target_language: str) -> tuple[Path, BooksModel]:
        translated_folder = Path(original_book.main_folder_path).parent / f"{Path(original_book.main_folder_path).name}_{target_language}"
        translated_folder.mkdir(parents=True, exist_ok=True)
        
        translated_title = self._translate_text(original_book.title, target_language) if original_book.title else original_book.title
        translated_description = self._translate_text(original_book.description, target_language) if original_book.description else original_book.description
        
        translated_book = BooksModel(
            title=f"{translated_title} ({target_language})",
            description=translated_description,
            author=original_book.author,
            contributor=original_book.contributor,
            category=original_book.category,
            publish_date=original_book.publish_date,
            publisher=original_book.publisher,
            language=target_language,
            cover_path=original_book.cover_path,
            main_folder_path=str(translated_folder),
            original_file_path=original_book.original_file_path,
            opf_path=original_book.opf_path,
            metadata_path=original_book.metadata_path,
            toc_path=original_book.toc_path,
            toc_content={},
            book_content=[],
            owner_id=original_book.owner_id,
            book_type=original_book.book_type,
        )
        
        with Session(self.engine) as session:
            session.add(translated_book)
            session.commit()
            session.refresh(translated_book)
        
        return translated_folder, translated_book

    def translate_book(
        self, 
        book: BooksModel, 
        target_language: str = "español",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        resume: bool = True
    ) -> dict:
        if not book.book_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book has no content to translate"
            )

        progress_data = self._load_progress(book.id, 'translation') if resume else None
        
        if progress_data and progress_data.get('translated_book_id'):
            with Session(self.engine) as session:
                translated_book = session.query(BooksModel).filter(
                    BooksModel.id == progress_data['translated_book_id']
                ).first()
                if not translated_book:
                    progress_data = None
                else:
                    translated_folder = Path(translated_book.main_folder_path)
                    translated_chapter_paths = list(translated_book.book_content) if translated_book.book_content else []
        
        if not progress_data:
            translated_folder, translated_book = self._create_translated_book_structure(book, target_language)
            translated_chapter_paths = []
        
        start_chapter = progress_data['last_chapter'] + 1 if progress_data else 0
        total_chapters = len(book.book_content)
        failed_chapters = []
        translated_toc = dict(translated_book.toc_content) if translated_book.toc_content else {}

        for chapter_index in range(start_chapter, total_chapters):
            chapter_path = book.book_content[chapter_index]
            
            if not Path(chapter_path).exists():
                failed_chapters.append({
                    'chapter': chapter_index + 1,
                    'error': 'File not found'
                })
                continue

            try:
                html_content = self._extract_text_from_html(chapter_path)
                chunks = self._chunk_html_content(html_content)
                
                translated_chunks = []
                for chunk_index, chunk in enumerate(chunks):
                    if progress_callback:
                        progress_callback(
                            chapter_index + 1,
                            total_chapters,
                            f"Traduciendo capítulo {chapter_index + 1}/{total_chapters}, fragmento {chunk_index + 1}/{len(chunks)}"
                        )
                    
                    translated_chunk = self._translate_chunk(chunk, target_language)
                    translated_chunks.append(translated_chunk)
                
                translated_content = ''.join(translated_chunks)
                
                original_path = Path(chapter_path)
                new_chapter_path = translated_folder / f"chapter_{chapter_index + 1}{original_path.suffix}"
                
                with open(new_chapter_path, 'w', encoding='utf-8') as f:
                    f.write(translated_content)
                
                translated_chapter_paths.append(str(new_chapter_path))
                
                with Session(self.engine) as session:
                    tb = session.query(BooksModel).filter(
                        BooksModel.id == translated_book.id
                    ).first()
                    tb.book_content = translated_chapter_paths
                    session.commit()
                
                self._save_progress(book.id, {
                    'last_chapter': chapter_index,
                    'translated_book_id': translated_book.id,
                    'target_language': target_language,
                    'total_chapters': total_chapters
                }, 'translation')
                
            except Exception as e:
                failed_chapters.append({
                    'chapter': chapter_index + 1,
                    'error': str(e)
                })
                continue

        if book.toc_content and not translated_toc:
            for toc_title, toc_path in book.toc_content.items():
                try:
                    translated_toc_title = self._translate_text(toc_title, target_language)
                    translated_toc[translated_toc_title] = toc_path
                except Exception:
                    translated_toc[toc_title] = toc_path

        with Session(self.engine) as session:
            translated_book = session.query(BooksModel).filter(
                BooksModel.id == translated_book.id
            ).first()
            translated_book.book_content = translated_chapter_paths
            translated_book.toc_content = translated_toc
            session.commit()
            session.refresh(translated_book)

        progress_file = Path(f'./content/progress/translation_{book.id}.json')
        if progress_file.exists():
            progress_file.unlink()

        return {
            'original_book_id': book.id,
            'translated_book_id': translated_book.id,
            'target_language': target_language,
            'translated_book': translated_book.serialize(),
            'total_chapters': total_chapters,
            'successful_chapters': len(translated_chapter_paths),
            'failed_chapters': failed_chapters
        }

    def summarize_book(
        self,
        book: BooksModel,
        language: str = "español",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        if not book.book_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book has no content to summarize"
            )
        
        self._save_progress(book.id, {
            'status': 'started',
            'current_chapter': 0,
            'total_chapters': len(book.book_content)
        }, 'summary')
        
        partial_summaries = []
        total_chapters = len(book.book_content)
        
        for chapter_index, chapter_path in enumerate(book.book_content):
            if not Path(chapter_path).exists():
                continue
                
            if progress_callback:
                progress_callback(
                    chapter_index + 1,
                    total_chapters,
                    f"Resumiendo capítulo {chapter_index + 1}/{total_chapters}"
                )
            
            self._save_progress(book.id, {
                'status': 'processing',
                'current_chapter': chapter_index + 1,
                'total_chapters': total_chapters
            }, 'summary')
            
            try:
                clean_text = self._extract_clean_text(chapter_path)
                if len(clean_text) > 50000:
                    clean_text = clean_text[:50000]
                    
                prompt = self.summary_prompt.format(title=book.title, content=clean_text)
                resp = self.client.models.generate_content(model=self.model_name, contents=prompt)
                partial_summaries.append({
                    'chapter': chapter_index + 1,
                    'summary': resp.text
                })
            except Exception as e:
                partial_summaries.append({
                    'chapter': chapter_index + 1,
                    'summary': f"Error al resumir: {str(e)}"
                })
        
        summaries_text = '\n\n'.join([
            f"Capítulo {s['chapter']}:\n{s['summary']}" 
            for s in partial_summaries
        ])
        
        final_prompt = self.final_summary_prompt.format(
            title=book.title,
            author=book.author or "Unknown",
            partial_summaries=summaries_text
        )
        
        try:
            final_resp = self.client.models.generate_content(model=self.model_name, contents=final_prompt)
            final_summary = final_resp.text
        except Exception as e:
            final_summary = f"Error al generar resumen final: {str(e)}"
        
        result = {
            'book_id': book.id,
            'title': book.title,
            'author': book.author,
            'summary': final_summary,
            'partial_summaries': partial_summaries,
            'language': language,
            'chapters_analyzed': len(book.book_content),
        }
        
        saved_paths = self._save_summary(book, language, result)
        result['saved_to'] = saved_paths
        
        progress_file = Path(f'./content/progress/summary_{book.id}.json')
        if progress_file.exists():
            progress_file.unlink()
        
        return result

    def translate_chapter(
        self, 
        chapter_path: str, 
        target_language: str = "español",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> str:
        if not Path(chapter_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chapter file not found"
            )

        html_content = self._extract_text_from_html(chapter_path)
        chunks = self._chunk_html_content(html_content)
        
        translated_chunks = []
        for chunk_index, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(
                    chunk_index + 1,
                    len(chunks),
                    f"Traduciendo fragmento {chunk_index + 1}/{len(chunks)}"
                )
            
            translated_chunk = self._translate_chunk(chunk, target_language)
            translated_chunks.append(translated_chunk)

        return ''.join(translated_chunks)

    def get_translation_progress(self, book_id: int) -> Optional[dict]:
        return self._load_progress(book_id, 'translation')

    def get_summary_progress(self, book_id: int) -> Optional[dict]:
        return self._load_progress(book_id, 'summary')

    def cancel_translation(self, book_id: int) -> bool:
        progress_file = Path(f'./content/progress/translation_{book_id}.json')
        if progress_file.exists():
            progress_file.unlink()
            return True
        return False

    def _summaries_dir(self) -> Path:
        p = Path('./content/summaries')
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _summary_base(self, book_id: int, language: str) -> Path:
        return self._summaries_dir() / f'book_{book_id}_{language}'

    def _save_summary(self, book: BooksModel, language: str, data: dict) -> dict:
        base = self._summary_base(book.id, language)
        json_path = base.with_suffix('.json')
        md_path = base.with_suffix('.md')
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(data.get('summary', ''))
            
        return {
            'json_path': str(json_path),
            'markdown_path': str(md_path)
        }

    def get_book_summaries(self, book: BooksModel) -> list[dict]:
        out_dir = self._summaries_dir()
        pattern = f'book_{book.id}_*.json'
        items = []
        
        for p in out_dir.glob(pattern):
            lang = p.stem.split(f'book_{book.id}_', 1)[1]
            md = p.with_suffix('.md')
            
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
                
            items.append({
                'language': lang,
                'json_path': str(p),
                'markdown_path': str(md),
                'title': data.get('title'),
                'author': data.get('author'),
                'chapters_analyzed': data.get('chapters_analyzed', 0),
                'updated_at_epoch': os.path.getmtime(p)
            })
            
        items.sort(key=lambda x: x['updated_at_epoch'], reverse=True)
        return items

    def get_summary_by_language(self, book: BooksModel, language: str) -> Optional[dict]:
        json_path = self._summary_base(book.id, language).with_suffix('.json')
        if not json_path.exists():
            return None
            
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_summary(self, book: BooksModel, language: str) -> bool:
        ok = False
        json_path = self._summary_base(book.id, language).with_suffix('.json')
        md_path = self._summary_base(book.id, language).with_suffix('.md')
        
        if json_path.exists():
            json_path.unlink()
            ok = True
            
        if md_path.exists():
            md_path.unlink()
            ok = True
            
        return ok

    def get_book_translations(self, book: BooksModel) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.query(BooksModel).filter(
                BooksModel.original_file_path == book.original_file_path,
                BooksModel.id != book.id
            ).all()
            return [r.serialize() for r in rows]