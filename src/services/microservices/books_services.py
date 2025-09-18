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

from src.models.users_model import UsersModel
from src.utils.http.response_utils import HttpResponses

class BooksServices:
    def __init__(self) -> None:
        super().__init__()
        self.books_sufix = ['.epub']
        self.engine: Engine = self.engine

    def save_book(self, file: UploadFile, user: UsersModel) -> None:
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
        extracted_folder = None

        # Guardamos el archivo.
        with open(original_file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
            print(f'The file {file.filename} was saved in {str(saving_folder)}')

        # Descomprimimos el archivo si es un .epub
        if path.suffix == '.epub':
            with zipfile.ZipFile(original_file_path, 'r') as zip_ref:
                extracted_folder = saving_folder / 'extracted'
                zip_ref.extractall(extracted_folder)

            # Validamos si el archivo de metadatos existe.
            metadata_path = extracted_folder / 'META-INF' / 'container.xml'
            if not metadata_path.exists():
                shutil.rmtree(saving_folder)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The EPUB file is missing the container.xml metadata file.",
                )
                # TODO: ...
                # TODO: Parsear el archivo de metadatos y guardar la información en la base de datos.