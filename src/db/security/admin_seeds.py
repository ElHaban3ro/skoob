# src/db/security/admin_seeds.py
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ADMIN_SLOTS: Tuple[int] = (1, 2, 3, 4)

class AdminSeedSettings(BaseSettings):
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 5432
    JWT_SECRET_KEY: str

    ADMIN1_NAME: Optional[str] = None
    ADMIN1_EMAIL: Optional[EmailStr] = None
    ADMIN1_PASSWORD: Optional[str] = None
    ADMIN1_USERNAME: Optional[str] = None

    ADMIN2_NAME: Optional[str] = None
    ADMIN2_EMAIL: Optional[EmailStr] = None
    ADMIN2_PASSWORD: Optional[str] = None
    ADMIN2_USERNAME: Optional[str] = None

    ADMIN3_NAME: Optional[str] = None
    ADMIN3_EMAIL: Optional[EmailStr] = None
    ADMIN3_PASSWORD: Optional[str] = None
    ADMIN3_USERNAME: Optional[str] = None

    ADMIN4_NAME: Optional[str] = None
    ADMIN4_EMAIL: Optional[EmailStr] = None
    ADMIN4_PASSWORD: Optional[str] = None
    ADMIN4_USERNAME: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

# normalizacion
def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _norm_lower(s: Optional[str]) -> str:
    return (s or "").strip().lower()

def default_admins_from_env() -> List[Dict[str, str]]:
    s = AdminSeedSettings()
    admins: List[Dict[str, str]] = []
    for i in ADMIN_SLOTS:
        name = getattr(s, f"ADMIN{i}_NAME")
        email = getattr(s, f"ADMIN{i}_EMAIL")
        password = getattr(s, f"ADMIN{i}_PASSWORD")
        username = getattr(s, f"ADMIN{i}_USERNAME")
        if name and email and password:
            uname = _norm_lower(username) or _norm_lower(str(email).split("@")[0])
            admins.append({
                "name": _norm(name),
                "email": _norm_lower(str(email)),
                "password": _norm(password),
                "username": uname,
            })
    return admins

def admin_env_index() -> Dict[str, Dict[str, str]]:
    idx: Dict[str, Dict[str, str]] = {}
    for a in default_admins_from_env():
        u = _norm_lower(a.get("username"))
        if u:
            idx[u] = a
    return idx
