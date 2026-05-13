from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.paths import DATA_PROCESSED


def _load_env_file_if_exists() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _dsn() -> str:
    _load_env_file_if_exists()
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    values = {k: os.getenv(k) for k in required}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise RuntimeError(f"Missing DB env vars: {', '.join(missing)}")
    return (
        f"host={values['DB_HOST']} "
        f"port={values['DB_PORT']} "
        f"dbname={values['DB_NAME']} "
        f"user={values['DB_USER']} "
        f"password={values['DB_PASSWORD']}"
    )


def _table(split: str) -> str:
    if split == "train":
        return "train_samples"
    if split == "val":
        return "val_samples"
    raise ValueError(split)


def _load_split(root: Path, split: str) -> tuple[pd.DataFrame, pd.Series]:
    x_name = "X_train.csv" if split == "train" else "X_test.csv"
    y_name = "y_train.csv" if split == "train" else "y_test.csv"
    x = pd.read_csv(root / DATA_PROCESSED.name / x_name)
    y_df = pd.read_csv(root / DATA_PROCESSED.name / y_name)
    target_col = y_df.columns[0]
    return x, y_df[target_col]


def main() -> int:
    parser = argparse.ArgumentParser(description="Load train/val datasets into PostgreSQL")
    parser.add_argument("--split", choices=["train", "val"], required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    args = parser.parse_args()

    data_root = args.root
    x, y = _load_split(data_root, args.split)
    table_name = _table(args.split)

    with psycopg.connect(_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id BIGSERIAL PRIMARY KEY,
                    features_json JSONB NOT NULL,
                    target_value DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(f"TRUNCATE TABLE {table_name}")
            for i in range(len(x)):
                cur.execute(
                    f"INSERT INTO {table_name} (features_json, target_value) VALUES (%s, %s)",
                    (Json(x.iloc[i].to_dict()), float(y.iloc[i])),
                )
        conn.commit()

    print(f"Loaded {len(x)} rows into {table_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())