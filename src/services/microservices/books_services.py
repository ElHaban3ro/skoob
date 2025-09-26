import os
from pathlib import Path, PosixPath
import shutil
from typing import Annotated, Optional, Union
from fastapi import HTTPException, status
from urllib import response
from fastapi import UploadFile
from sqlalchemy import Engine
import uuid
import zipfile
from sqlalchemy.orm import Session
from lxml import etree, html
import pprint

from src.models.users_model import UsersModel
from src.models.books_model import BooksModel
from src.utils.http.response_utils import HttpResponses

class BooksServices:
    def __init__(self) -> None:
        super().__init__()
        self.books_sufix = ['.epub']
        self.books_content_prefix = '/books/content'
        # =========================== NAMESPACES XML ============================
        # Los namespaces son como espacios que definen el contexto o grupos de 
        # elementos en un documento XML. 
        self.namespaces = {'a': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        self.opf_namespaces = ns = {
            "opf": "http://www.idpf.org/2007/opf",
            "dc": "http://purl.org/dc/elements/1.1/"
        }
        self.ncx_namespaces = {
            "ncx": "http://www.daisy.org/z3986/2005/ncx/"
        }
        # ========================================================================

        self.engine: Engine = self.engine

    def save_book(self, file: UploadFile, user: UsersModel) -> BooksModel:
        path = Path(file.filename) # lo convertimos a formato path.
        if path.suffix not in self.books_sufix: # verificamos que el formato sea correcto.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File format not supported",
            )
        # Generamos el path donde guardaremos el archivo.
        saving_folder: PosixPath = Path('.') / 'content' / 'books' / user.email / str(uuid.uuid4())
        
        # Validamos la existencia de la carpeta de guardado.
        if not saving_folder.exists():
            os.makedirs(saving_folder)

        # Guardamos el archivo, con un nombre distinto dependiendo de su formato.
        if path.suffix == '.epub':
            filename = Path('book_content_epub.zip')
        else:
            filename = Path('book' + path.suffix)
        
        # Guardamos el path del archivo original.
        original_file_path = saving_folder / filename

        # Guardamos el archivo.
        with open(original_file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
            #print(f'The file {file.filename} was saved in {str(saving_folder)}')

        # Descomprimimos el archivo si es un .epub
        if path.suffix == '.epub':
            book_content = {'type': 'epub', 'data': self.process_epub_book(original_file_path, saving_folder)}
        else:
            pass
            
        book = BooksModel(
            title=book_content['data']['metadata']['title'],
            description=book_content['data']['metadata']['description'],
            author=book_content['data']['metadata']['creator'],
            contributor=book_content['data']['metadata']['contributor'],
            category=book_content['data']['metadata']['category'],
            publish_date=book_content['data']['metadata']['publish_date'],
            publisher=book_content['data']['metadata']['publisher'],
            language=book_content['data']['metadata']['language'],
            cover_path=self.safety_path(saving_folder, book_content['data']['metadata']['cover_path']),
            main_folder_path=str(saving_folder),
            original_file_path=str(original_file_path),
            opf_path=self.safety_path(saving_folder, book_content['data']['metadata']['opf_path']),
            metadata_path=self.safety_path(saving_folder, book_content['data']['metadata']['metadata_base_path']),
            toc_path=self.safety_path(saving_folder, book_content['data']['metadata']['content_table_path']),
            toc_content=book_content['data']['toc'],
            book_content=book_content['data']['book_content'],
            owner_id=user.id,
            book_type='epub' if path.suffix == '.epub' else 'pdf',
        )
        with Session(self.engine) as session:
            session.add(book)
            session.commit()
            session.refresh(book)
        self.edit_book_urls(book)

        return book
    
    def safety_path(self, safety_base: PosixPath, target_path: Union[str, None] = None) -> str:
        """Verifica que el path objetivo esté dentro del path base de seguridad. El path absoluto DEBE estar dentro del a ruta de extracción del libro, sino, se considera un intento de acceso no autorizado.

        Returns:
            str: Devuelve el path objetivo si es seguro, de lo contrario devuelve None. 
        """
        if str(safety_base) not in str(Path(target_path).resolve()) or not target_path:
            return None
        return target_path


    def edit_book_urls(self, book: BooksModel) -> None:
        """Edita las URLs de los archivos del libro para que sean accesibles desde la API.

        Args:
            book (BooksModel): Instancia del libro a editar.
        """
        ns = {"xlink": "http://www.w3.org/1999/xlink"}
        for chapter in book.book_content:
            chapter_path = Path(chapter)
            tree = html.parse(chapter_path)
            src_nodes = tree.xpath("//*[@src]")
            for node in src_nodes:
                src = node.get("src")
                if '.' in src:
                    src = src.replace('..', '')
                    src = src.replace('//', '/')
                node.set('src', f"{self.books_content_prefix}/{book.id}{src}")

            href_nodes = tree.xpath("//*[@href]")
            for node in href_nodes:
                href = node.get("href")
                if '.' in href:
                    href = href.replace('..', '')
                    href = href.replace('//', '/')
                node.set('href', f"{self.books_content_prefix}/{book.id}{href}")
            tree.write(chapter_path, encoding='utf-8', method='xml', pretty_print=True)
            
            xml_tree = etree.parse(chapter_path)
            xlinkhref_nodes = xml_tree.xpath(f"//*[@xlink:href]", namespaces=ns)
            for node in xlinkhref_nodes:
                xlinkhref = node.get(f"{{{ns['xlink']}}}href")
                if '.' in xlinkhref:
                    xlinkhref = xlinkhref.replace('..', '')
                    xlinkhref = xlinkhref.replace('//', '/')
                node.set(f"{{{ns['xlink']}}}href", f"{self.books_content_prefix}/{book.id}{xlinkhref}")
            xml_tree.write(chapter_path, encoding='utf-8', xml_declaration=True, pretty_print=True)

    def process_epub_book(self, original_file_path: PosixPath, saving_folder: PosixPath) -> None:
        """_summary_
        """        
        with zipfile.ZipFile(original_file_path, 'r') as zip_ref:
            extracted_folder = saving_folder / 'extracted'
            zip_ref.extractall(extracted_folder)

        # Validamos si el archivo de metadatos existe.
        metadata_info_path = extracted_folder / 'META-INF' / 'container.xml'
        if not metadata_info_path.exists():
            shutil.rmtree(saving_folder)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The EPUB file is missing the container.xml metadata file.",
            )
        
        # Parseamos el archivo XML.
        tree = etree.parse(metadata_info_path)
        root = tree.getroot() # obtenemos la raiz del XML.

        # Buscamos 'rootfile' dentro del XML teniendo en 
        # cuenta el contexto del namespace 'a'.
        _rootfile_ = root.xpath('//a:rootfile', namespaces=self.namespaces)[0]

        # El archivo OPF contiene los metadatos del libro. Generamos su path.
        opf_path = extracted_folder / _rootfile_.get('full-path')
        metadata = self.read_opf(opf_path, saving_folder)
        print(metadata)
        metadata['metadata']['metadata_base_path'] = str(opf_path.parent)
        metadata['metadata']['opf_path'] = str(opf_path)
        return metadata

    def read_opf(self, opf_path: PosixPath, saving_path: PosixPath) -> dict:
        """Lee el archivo OPF y extrae los metadatos del libro.

        Args:
            opf_path (str): Path del archivo OPF.

        Returns:
            dict: Devuelve los metadatos del libro.
        """        
        # Validamos la existencia del archivo OPF.
        if not opf_path.exists():
            shutil.rmtree(saving_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The OPF (metadata) file does not exist.",
            )
        
        # Parseamos el archivo OPF.
        tree = etree.parse(opf_path)
        root = tree.getroot() # obtenemos la raiz del XML.

        # Extraemos los metadatos del libro.
        metadata = root.find('opf:metadata', namespaces=self.opf_namespaces)
        if metadata is None:
            shutil.rmtree(saving_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The OPF file is missing the metadata section.",
            )
        
        cover_id = metadata.find("opf:meta[@name='cover']", namespaces=self.opf_namespaces).get('content') if metadata.find("opf:meta[@name='cover']", namespaces=self.opf_namespaces) is not None else None
        cover_path = None

        if cover_id:
            cover_item = root.find(f".//opf:item[@id='{cover_id}']", namespaces=self.opf_namespaces)
            if cover_item is not None:
                cover_path = opf_path.parent / cover_item.get('href')
        
        # Extraemos los metadatos específicos.
        metadata = {
            'title': metadata.find('dc:title', namespaces=self.opf_namespaces).text if metadata.find('dc:title', namespaces=self.opf_namespaces) is not None else 'Unknown, the aventures of Fernando',
            'description': metadata.find('dc:description', namespaces=self.opf_namespaces).text if metadata.find('dc:description', namespaces=self.opf_namespaces) is not None else 'No description.',
            'creator': metadata.find('dc:creator', namespaces=self.opf_namespaces).text if metadata.find('dc:creator', namespaces=self.opf_namespaces) is not None else 'Unknown',
            'contributor': metadata.find('dc:contributor', namespaces=self.opf_namespaces).text if metadata.find('dc:contributor', namespaces=self.opf_namespaces) is not None else 'ElHaban3ro (Unknown)',
            'category': metadata.find('dc:subject', namespaces=self.opf_namespaces).text if metadata.find('dc:subject', namespaces=self.opf_namespaces) is not None else None,
            'publish_date': metadata.find('dc:date', namespaces=self.opf_namespaces).text if metadata.find('dc:date', namespaces=self.opf_namespaces) is not None else None,
            'publisher': metadata.find('dc:publisher', namespaces=self.opf_namespaces).text if metadata.find('dc:publisher', namespaces=self.opf_namespaces) is not None else None,
            'language': metadata.find('dc:language', namespaces=self.opf_namespaces).text if metadata.find('dc:language', namespaces=self.opf_namespaces) is not None else None,
            'cover_path': str(cover_path) if cover_path and cover_path.exists() else None,
        }

        # Accedemos a los elementos que 
        # componen el libro (se presentan en orden).
        _spine_ = root.find('opf:spine', namespaces=self.opf_namespaces)
        book_content = []

        # Recorremos los elementos del libro, estos estan ordenados.
        for content in _spine_:
            content_ref = content.get('idref') # Obtenemos el ID de esta parte.

            # Buscamos el elemento que contiene el path de este ID.
            content = root.find(f".//opf:item[@id='{content_ref}']", namespaces=self.opf_namespaces)
            content_path = opf_path.parent / content.get('href') # Construimos el path completo.
            book_content.append(str(content_path)) # Guardamos el path en la lista.
        
        # Obtenemos el path del TOC (Tabla de Contenidos) si existe.
        toc_ref = _spine_.get('toc')
        toc = {}
        if toc_ref != None:
            # Buscamos el elemento que contiene el path del TOC.
            toc_obj = root.find(f".//opf:item[@id='{toc_ref}']", namespaces=self.opf_namespaces)
            # Guardamos el path del TOC en los metadatos.
            metadata['content_table_path'] = str(opf_path.parent / toc_obj.get('href'))

            # Parseamos el archivo NCX (TOC).
            toc_tree = etree.parse(metadata['content_table_path'])
            toc_root = toc_tree.getroot()

            # Buscamos los navPoints (puntos de navegación) en el TOC.
            toc_navpoints = toc_root.findall('.//ncx:navPoint', namespaces=self.ncx_namespaces)

            for navpoint in toc_navpoints:
                # Obtenemos el título de ese punto.
                nav_label = navpoint.find('ncx:navLabel/ncx:text', namespaces=self.ncx_namespaces).text
                # Obtenemos el path de ese punto y lo convertimos a un path completo.
                nav_path = opf_path.parent / navpoint.find('ncx:content', namespaces=self.ncx_namespaces).get('src')
                toc[nav_label] = str(nav_path)
        return {'metadata': metadata, 'toc': toc, 'book_content': book_content}
    
    def get_book(self, id: int) -> BooksModel:
        with Session(self.engine) as session:
            book = session.query(BooksModel).filter(BooksModel.id == id).first()
            return book
        
    def get_all_books(self) -> list[BooksModel]:
        with Session(self.engine) as session:
            books = session.query(BooksModel).all()
            return books
        
    def get_all_my_books(self, user: UsersModel) -> list[BooksModel]:
        with Session(self.engine) as session:
            books = session.query(BooksModel).filter(BooksModel.owner_id == user.id).all()
            return books
        
    def delete_book(self, id: int) -> bool:
        with Session(self.engine) as session:
            book = session.query(BooksModel).filter(BooksModel.id == id).first()
            if not book:
                return False
            # Eliminamos el libro de la base de datos.
            session.delete(book)
            session.commit()
            # Eliminamos los archivos del libro.
            if Path(book.main_folder_path).exists():
                shutil.rmtree(book.main_folder_path)
            return True
        
    def read_book(self, book_id: int, chapter: int) -> str:
        """Obtiene la ruta del capítulo solicitado.

        Args:
            book_id (int): ID del libro.
            chapter (int): Capítulo a leer.

        Returns:
            str: Devuelve el path del capítulo solicitado.
        """        
        with Session(self.engine) as session:
            book = session.query(BooksModel).filter(BooksModel.id == book_id).first()
            if chapter <= 0 or chapter > len(book.book_content):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The chapter number is out of range.",
                )
            chapter_path = book.book_content[chapter - 1]
            if not Path(chapter_path).exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="The chapter file does not exist.",
                )
            return chapter_path