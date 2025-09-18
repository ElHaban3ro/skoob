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
from lxml import etree
import pprint

from src.models.users_model import UsersModel
from src.models.books_model import BooksModel
from src.utils.http.response_utils import HttpResponses

class BooksServices:
    def __init__(self) -> None:
        super().__init__()
        self.books_sufix = ['.epub']

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
            title=book_content['data']['medatada']['title'],
            description=book_content['data']['medatada']['description'],
            author=book_content['data']['medatada']['creator'],
            contributor=book_content['data']['medatada']['contributor'],
            category=book_content['data']['medatada']['category'],
            publish_date=book_content['data']['medatada']['publish_date'],
            publisher=book_content['data']['medatada']['publisher'],
            language=book_content['data']['medatada']['language'],
            main_folder_path=str(saving_folder),
            original_file_path=str(original_file_path),
            opf_path=book_content['data']['medatada']['content_table_path'],
            metadata_path=str(book_content['data']['metadata_base_file_path']),
            toc_path=book_content['data']['medatada']['content_table_path'],
            owner_id=user.id,
            book_type='epub' if path.suffix == '.epub' else 'pdf',
        )
        with Session(self.engine) as session:
            session.add(book)
            session.commit()
            session.refresh(book)

        return book

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
        metadata['metadata_base_file_path'] = str(opf_path.parent)
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
        return {'medatada': metadata, 'toc': toc, 'book_content': book_content}
    
    def get_book(self, id: int) -> BooksModel:
        with Session(self.engine) as session:
            book = session.query(BooksModel).filter(BooksModel.id == id).first()
            return book
        
    def get_all_books(self) -> list[BooksModel]:
        with Session(self.engine) as session:
            books = session.query(BooksModel).all()
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