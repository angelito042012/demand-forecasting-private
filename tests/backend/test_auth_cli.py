"""Pruebas del hash de contrasenas y de la CLI create-user (base temporal aislada)."""
# ruff: noqa: F401, F811  (fixtures importadas de test_auth_common)
from __future__ import annotations

import pytest
from pymongo import MongoClient

from backend import cli
from backend.app.auth import passwords
from backend.app.config import Settings
from tests.backend.test_auth_common import db


def test_scrypt_format_and_verification():
    h = passwords.hash_password("una-clave-larga-1")
    scheme, n, r, p, _salt, _digest = h.split("$")
    assert (scheme, n, r, p) == ("scrypt", "32768", "8", "1")
    assert h != passwords.hash_password("una-clave-larga-1")  # sal aleatoria
    assert passwords.verify_password("una-clave-larga-1", h)
    assert not passwords.verify_password("otra-clave-larga-1", h)
    assert not passwords.verify_password("x", "formato-invalido")
    assert not passwords.verify_password("x", "scrypt$99999999$8$1$AA==$AA==")  # parametros abusivos


def test_validators():
    assert passwords.validate_password("a" * 11)
    assert passwords.validate_password("a" * 12) is None
    assert passwords.validate_username("Ab")
    assert passwords.validate_username("ana.perez") is None


@pytest.fixture
def cli_env(db, monkeypatch):
    s = Settings(_env_file=None, mongodb_database=db.name)
    monkeypatch.setattr(cli, "get_settings", lambda: s)
    return db


def test_cli_creates_user_without_printing_password(cli_env, monkeypatch, capsys):
    monkeypatch.setenv("DF_NEW_PASSWORD", "clave-cli-muy-larga-1")
    assert cli.main(["create-user", "--username", "Operador", "--role", "lector"]) == 0
    out = capsys.readouterr()
    assert "clave-cli" not in out.out + out.err
    u = cli_env["users"].find_one({"username": "operador"})
    assert u["role"] == "lector" and u["active"] and "clave-cli" not in u["password_hash"]
    assert passwords.verify_password("clave-cli-muy-larga-1", u["password_hash"])


def test_cli_does_not_overwrite_existing(cli_env, monkeypatch, capsys):
    monkeypatch.setenv("DF_NEW_PASSWORD", "clave-cli-muy-larga-1")
    assert cli.main(["create-user", "--username", "dup", "--role", "admin"]) == 0
    original = cli_env["users"].find_one({"username": "dup"})["password_hash"]
    monkeypatch.setenv("DF_NEW_PASSWORD", "otra-clave-muy-larga-2")
    assert cli.main(["create-user", "--username", "dup", "--role", "lector"]) == 1
    doc = cli_env["users"].find_one({"username": "dup"})
    assert doc["password_hash"] == original and doc["role"] == "admin"


def test_cli_rejects_short_password_and_bad_role(cli_env, monkeypatch):
    monkeypatch.setenv("DF_NEW_PASSWORD", "corta")
    assert cli.main(["create-user", "--username", "corto", "--role", "admin"]) == 2
    assert cli_env["users"].count_documents({}) == 0
    with pytest.raises(SystemExit):
        cli.main(["create-user", "--username", "x1234", "--role", "root"])


def test_cli_has_no_password_argument():
    with pytest.raises(SystemExit):
        cli.main(["create-user", "--username", "abc", "--role", "admin", "--password", "clave-larga-123"])


def test_cli_uses_getpass_when_no_env(cli_env, monkeypatch):
    monkeypatch.delenv("DF_NEW_PASSWORD", raising=False)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "clave-getpass-larga-1")
    assert cli.main(["create-user", "--username", "porgetpass", "--role", "admin"]) == 0
    assert MongoClient is not None and cli_env["users"].count_documents({"username": "porgetpass"}) == 1
