from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _get_model_version(model_path: Path | None) -> str:
    if model_path is None:
        return "unknown"
    try:
        return model_path.resolve().name
    except Exception:
        return str(model_path)


def _vault_kv_path() -> str:
    # KV v2: путь вида secret/data/<logical> (без ведущего /)
    return os.getenv("VAULT_SECRET_PATH", "secret/data/housing/db").lstrip("/")


def _load_db_settings_from_vault() -> dict[str, str] | None:
    """Читает учётные данные и параметры БД из HashiCorp Vault (KV v2)."""
    addr = (os.getenv("VAULT_ADDR") or "").rstrip("/")
    token = os.getenv("VAULT_TOKEN") or ""
    if not addr or not token:
        return None
    path = _vault_kv_path()
    url = f"{addr}/v1/{path}"
    req = urllib.request.Request(url, headers={"X-Vault-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Vault HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Vault unreachable at {addr}: {e}") from e

    if "errors" in payload and payload["errors"]:
        raise RuntimeError(f"Vault error: {payload['errors']}")
    data = (payload.get("data") or {}).get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Vault response missing data.data object")
    out: dict[str, str] = {}
    for key in ("host", "port", "dbname", "username", "password"):
        val = data.get(key)
        if val is not None and str(val).strip() != "":
            out[key] = str(val)
    return out


def _get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    vault_data = _load_db_settings_from_vault()
    if vault_data:
        host = vault_data.get("host") or os.getenv("DB_HOST")
        port = vault_data.get("port") or os.getenv("DB_PORT")
        dbname = vault_data.get("dbname") or os.getenv("DB_NAME")
        user = vault_data.get("username") or os.getenv("DB_USER")
        password = vault_data.get("password") or os.getenv("DB_PASSWORD")
    else:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        dbname = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

    missing = [
        name
        for name, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_NAME": dbname,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not value
    ]
    if missing:
        missing_joined = ", ".join(missing)
        hint = (
            " Задайте VAULT_ADDR и VAULT_TOKEN для чтения секретов из Vault "
            "или передайте переменные DB_* / DATABASE_URL."
        )
        raise RuntimeError(f"Missing required DB environment variables: {missing_joined}.{hint}")

    return (
        f"host={host} "
        f"port={port} "
        f"dbname={dbname} "
        f"user={user} "
        f"password={password}"
    )


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(_get_dsn(), row_factory=dict_row)


def init_db() -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    features_json JSONB NOT NULL,
                    prediction_value DOUBLE PRECISION NOT NULL,
                    model_version TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ok'
                )
                """
            )
        conn.commit()


def save_prediction(
    *,
    features: dict[str, float],
    prediction_value: float,
    model_path: Path | None = None,
) -> int:
    from psycopg.types.json import Json

    model_version = _get_model_version(model_path)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions (features_json, prediction_value, model_version, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (Json(features), float(prediction_value), model_version, "ok"),
            )
            row: dict[str, Any] | None = cur.fetchone()
        conn.commit()

    if not row or "id" not in row:
        raise RuntimeError("Failed to save prediction: DB did not return inserted id")
    return int(row["id"])
