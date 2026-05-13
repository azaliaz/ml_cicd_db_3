from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split

from .logger import Logger, show_logs_from_env
from .paths import FEATURE_NAMES, ROOT, TARGET_NAME


def _preprocess_params_from_file(root: Path) -> dict:
    p = root / "params.yaml"
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("preprocess", {}) or {}


def run_preprocess(
    root: Path | None = None,
    test_size: float | None = None,
    random_state: int | None = None,
) -> None:
    root = root or ROOT
    log = Logger(show_logs_from_env()).get_logger(__name__)
    file_p = _preprocess_params_from_file(root)
    test_size = float(test_size if test_size is not None else file_p.get("test_size", 0.2))
    random_state = int(random_state if random_state is not None else file_p.get("random_state", 42))
    log.info("preprocess: root=%s test_size=%s random_state=%s", root, test_size, random_state)

    raw_dir = root / "data" / "raw"
    proc_dir = root / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = raw_dir / "california_housing.csv"
    if raw_csv.is_file():
        log.info("preprocess: используется существующий %s", raw_csv)
        df = pd.read_csv(raw_csv)
        missing = [c for c in FEATURE_NAMES + [TARGET_NAME] if c not in df.columns]
        if missing:
            raise ValueError(f"В {raw_csv} не хватает колонок: {missing}")
    else:
        log.info("preprocess: загрузка California Housing (sklearn)")
        # Кэш sklearn внутри проекта — удобно для CI и окружений без записи в $HOME
        sk_home = str(root / "data" / ".sklearn_cache")
        bunch = fetch_california_housing(as_frame=True, data_home=sk_home)
        df = bunch.frame
        df.to_csv(raw_csv, index=False)

    X = df[FEATURE_NAMES]
    y = df[TARGET_NAME]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    X_train.to_csv(proc_dir / "X_train.csv", index=False)
    X_test.to_csv(proc_dir / "X_test.csv", index=False)
    y_train.to_csv(proc_dir / "y_train.csv", index=False, header=True)
    y_test.to_csv(proc_dir / "y_test.csv", index=False, header=True)
    log.info("preprocess: готово train/test в %s", proc_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Подготовка данных California Housing")
    parser.add_argument("--root", type=Path, default=None, help="Корень проекта (по умолчанию рядом с src)")
    parser.add_argument("--test-size", type=float, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    args = parser.parse_args()
    run_preprocess(root=args.root, test_size=args.test_size, random_state=args.random_state)


if __name__ == "__main__":
    main()
