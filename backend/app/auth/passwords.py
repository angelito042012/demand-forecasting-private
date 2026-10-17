"""Hash de contrasenas con scrypt de la biblioteca estandar (docs/T08_CONTRATO.md §2)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

N, R, P = 2**15, 8, 1
SALT_BYTES = 16
DKLEN = 32
MAXMEM = 128 * 1024 * 1024
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,64}$")
ROLES = ("admin", "lector")


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=MAXMEM, dklen=DKLEN)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _scrypt(password, salt, N, R, P)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """Comparacion en tiempo constante; formato invalido o parametros fuera de rango -> False."""
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        n, r, p = int(n), int(r), int(p)
        if scheme != "scrypt" or n > 2**16 or r > 16 or p > 4 or n < 2:
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(hash_b64)
        digest = _scrypt(password, salt, n, r, p)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


_DUMMY: str | None = None


def dummy_verify(password: str) -> None:
    """Calculo ficticio para igualar tiempos cuando el usuario no existe o esta inactivo."""
    global _DUMMY
    if _DUMMY is None:
        _DUMMY = hash_password(secrets.token_urlsafe(16))
    verify_password(password, _DUMMY)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> str | None:
    """Devuelve mensaje de error o None."""
    if not USERNAME_RE.match(username):
        return "El usuario debe tener 3 a 64 caracteres: letras minusculas, digitos, punto, guion o guion bajo."
    return None


def validate_password(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"La contrasena debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"La contrasena no puede superar {MAX_PASSWORD_LENGTH} caracteres."
    return None
