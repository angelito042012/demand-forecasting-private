"""CLI local: python -m backend.cli create-user --username U --role admin|lector

La contrasena se lee de DF_NEW_PASSWORD o por getpass; nunca por argumento ni se imprime.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.auth.passwords import (
    ROLES,
    normalize_username,
    validate_password,
    validate_username,
)
from backend.app.auth.store import create_user
from backend.app.config import get_settings


def _read_password() -> str:
    env = os.environ.get("DF_NEW_PASSWORD")
    if env:
        return env
    first = getpass.getpass("Contrasena (min. 12 caracteres): ")
    if first != getpass.getpass("Repita la contrasena: "):
        raise SystemExit("Las contrasenas no coinciden.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cu = sub.add_parser("create-user", help="Crea un usuario (no sobrescribe existentes).")
    cu.add_argument("--username", required=True)
    cu.add_argument("--role", required=True, choices=ROLES)
    args = parser.parse_args(argv)

    username = normalize_username(args.username)
    problem = validate_username(username)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    password = _read_password()
    problem = validate_password(password)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    settings = get_settings()
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, appname="demand-forecasting-cli")
    try:
        created = create_user(client[settings.mongodb_database], username, args.role, password)
    except PyMongoError:
        print("No se pudo acceder a la base de datos.", file=sys.stderr)
        return 3
    finally:
        client.close()
    if not created:
        print(f"El usuario '{username}' ya existe; no se modifico.", file=sys.stderr)
        return 1
    print(f"Usuario '{username}' creado con rol {args.role}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
