from typing import Optional, Union
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated

from passlib.hash import pbkdf2_sha256

class SecurityServices:
    def __init__(self) -> None:
        """Servicios proporcionados para facilitar las operaciones de seguirdad.
        """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea una password y devuelve su hash.

        Args:
            password (str): Password a hashear.

        Returns:
            str: Devuelve el Hash.
        """        
        return pbkdf2_sha256.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica si una password en texto plano coincide con su hash.

        Args:
            plain_password (str): Password en texto plano.
            hashed_password (str): Hash de la password.

        Returns:
            bool: Devuelve True si coinciden, False en caso contrario.
        """        
        return pbkdf2_sha256.verify(plain_password, hashed_password)