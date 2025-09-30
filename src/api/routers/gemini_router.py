from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel

from src.services.core_services import CoreServices
from src.utils.http.response_utils import HttpResponses


class TranslateBookRequest(BaseModel):
    book_id: int
    target_language: str = "español"
    resume: bool = True


class SummarizeBookRequest(BaseModel):
    book_id: int
    language: str = "español"


class TranslateChapterRequest(BaseModel):
    book_id: int
    chapter_number: int
    target_language: str = "español"


class GeminiRouter:
    """
   
    """
    def __init__(self, services: CoreServices) -> None:
        self.prefix: str = '/gemini'
        self.router: APIRouter = APIRouter()
        self.translation_progress: dict = {}
        
        def raise_authorized() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You don't have permission to perform this action"
            )

        def progress_callback(book_id: int, operation: str = 'translation'):
            def callback(current: int, total: int, message: str):
                key = f"{operation}_{book_id}"
                self.translation_progress[key] = {
                    'current': current,
                    'total': total,
                    'message': message,
                    'percentage': round((current / total) * 100, 2),
                    'status': 'running'
                }
            return callback

        @self.router.post('/translate/book', tags=['Gemini AI'])
        def translate_book(
            response: Response,
            request: TranslateBookRequest,
            background_tasks: BackgroundTasks,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(request.book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            saved_progress = services.gemini.get_translation_progress(request.book_id)
            if saved_progress and not request.resume:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_409_CONFLICT,
                    status_title='TranslationInProgress',
                    content_response={
                        'message': 'Translation in progress. Set resume=true to continue or cancel it first.',
                        'progress': saved_progress
                    }
                )

            def translate_task():
                try:
                    translation_result = services.gemini.translate_book(
                        book=book,
                        target_language=request.target_language,
                        progress_callback=progress_callback(request.book_id, 'translation'),
                        resume=request.resume
                    )
                    key = f"translation_{request.book_id}"
                    self.translation_progress[key] = {
                        'status': 'completed',
                        'result': translation_result
                    }
                except Exception as e:
                    key = f"translation_{request.book_id}"
                    self.translation_progress[key] = {
                        'status': 'failed',
                        'error': str(e)
                    }

            background_tasks.add_task(translate_task)
            
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_202_ACCEPTED,
                status_title='TranslationStarted',
                content_response={
                    'message': 'Translation started in background',
                    'book_id': request.book_id,
                    'check_progress_at': f'/gemini/translate/progress/{request.book_id}'
                }
            )

        @self.router.get('/translate/progress/{book_id}', tags=['Gemini AI'])
        def get_translation_progress(
            response: Response,
            book_id: int,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            key = f"translation_{book_id}"
            progress = self.translation_progress.get(key)
            
            if not progress:
                saved_progress = services.gemini.get_translation_progress(book_id)
                if saved_progress:
                    return HttpResponses.standard_response(
                        response=response,
                        status_code=status.HTTP_200_OK,
                        status_title='Ok',
                        content_response={
                            'status': 'paused',
                            'progress': saved_progress
                        }
                    )
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='NoTranslationInProgress',
                )

            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={'progress': progress}
            )

        @self.router.delete('/translate/cancel/{book_id}', tags=['Gemini AI'])
        def cancel_translation(
            response: Response,
            book_id: int,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            key = f"translation_{book_id}"
            if key in self.translation_progress:
                del self.translation_progress[key]
            
            cancelled = services.gemini.cancel_translation(book_id)
            
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={'cancelled': cancelled}
            )

        @self.router.post('/summarize/book', tags=['Gemini AI'])
        def summarize_book(
            response: Response,
            request: SummarizeBookRequest,
            background_tasks: BackgroundTasks,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(request.book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            key = f"summary_{request.book_id}"
            self.translation_progress[key] = {
                'status': 'starting',
                'current': 0,
                'total': len(book.book_content or []),
                'message': 'Iniciando resumen...',
                'percentage': 0.0
            }

            def summary_task():
                try:
                    summary_result = services.gemini.summarize_book(
                        book=book,
                        language=request.language,
                        progress_callback=progress_callback(request.book_id, 'summary')
                    )
                    self.translation_progress[key] = {
                        'status': 'completed',
                        'result': summary_result
                    }
                except Exception as e:
                    self.translation_progress[key] = {
                        'status': 'failed',
                        'error': str(e)
                    }

            background_tasks.add_task(summary_task)
            
            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_202_ACCEPTED,
                status_title='SummaryStarted',
                content_response={
                    'message': 'Summary generation started in background',
                    'book_id': request.book_id,
                    'check_progress_at': f'/gemini/summarize/progress/{request.book_id}'
                }
            )

        @self.router.get('/summarize/progress/{book_id}', tags=['Gemini AI'])
        def get_summary_progress(
            response: Response,
            book_id: int,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            key = f"summary_{book_id}"
            progress = self.translation_progress.get(key)
            
            if not progress:
                saved_progress = services.gemini.get_summary_progress(book_id)
                if saved_progress:
                    return HttpResponses.standard_response(
                        response=response,
                        status_code=status.HTTP_200_OK,
                        status_title='Ok',
                        content_response={
                            'status': 'paused',
                            'progress': saved_progress
                        }
                    )
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='NoSummaryInProgress',
                )

            return HttpResponses.standard_response(
                response=response,
                status_code=status.HTTP_200_OK,
                status_title='Ok',
                content_response={'progress': progress}
            )

        @self.router.post('/translate/chapter', tags=['Gemini AI'])
        def translate_chapter(
            response: Response,
            request: TranslateChapterRequest,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(request.book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            if request.chapter_number < 1 or request.chapter_number > len(book.book_content):
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status_title='InvalidChapterNumber',
                )

            try:
                chapter_path = book.book_content[request.chapter_number - 1]
                translated_content = services.gemini.translate_chapter(
                    chapter_path=chapter_path,
                    target_language=request.target_language,
                    progress_callback=progress_callback(request.book_id, f"chapter_{request.chapter_number}")
                )
                
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_200_OK,
                    status_title='Ok',
                    content_response={
                        'content': {
                            'chapter_number': request.chapter_number,
                            'translated_content': translated_content
                        }
                    }
                )
            except Exception as e:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status_title='ChapterTranslationError',
                    content_response={'error': str(e)}
                )

        @self.router.get('/translations/{book_id}', tags=['Gemini AI'])
        def get_book_translations(
            response: Response,
            book_id: int,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            try:
                translations = services.gemini.get_book_translations(book)
                
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_200_OK,
                    status_title='Ok',
                    content_response={
                        'original_book_id': book_id,
                        'translations': translations
                    }
                )
            except Exception as e:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status_title='Error',
                    content_response={'error': str(e)}
                )

        @self.router.get('/summaries/{book_id}', tags=['Gemini AI'])
        def get_book_summaries(
            response: Response,
            book_id: int,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            try:
                summaries = services.gemini.get_book_summaries(book)
                
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_200_OK,
                    status_title='Ok',
                    content_response={
                        'book_id': book_id,
                        'summaries': summaries
                    }
                )
            except Exception as e:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status_title='Error',
                    content_response={'error': str(e)}
                )

        @self.router.get('/summary/{book_id}/{language}', tags=['Gemini AI'])
        def get_summary_by_language(
            response: Response,
            book_id: int,
            language: str,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            try:
                summary = services.gemini.get_summary_by_language(book, language)
                
                if not summary:
                    return HttpResponses.standard_response(
                        response=response,
                        status_code=status.HTTP_404_NOT_FOUND,
                        status_title='SummaryNotFound',
                    )
                
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_200_OK,
                    status_title='Ok',
                    content_response={'summary': summary}
                )
            except Exception as e:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status_title='Error',
                    content_response={'error': str(e)}
                )

        @self.router.delete('/summary/{book_id}/{language}', tags=['Gemini AI'])
        def delete_summary(
            response: Response,
            book_id: int,
            language: str,
            user = Depends(services.get_current_user)
        ) -> dict[str, object]:
            book = services.get_book(book_id)
            if not book:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_404_NOT_FOUND,
                    status_title='BookNotFound',
                )
            
            if book.owner_id != user.id:
                raise_authorized()

            try:
                deleted = services.gemini.delete_summary(book, language)
                
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_200_OK,
                    status_title='Ok',
                    content_response={'deleted': deleted}
                )
            except Exception as e:
                return HttpResponses.standard_response(
                    response=response,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status_title='Error',
                    content_response={'error': str(e)}
                )