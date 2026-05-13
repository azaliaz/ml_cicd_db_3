"""
обучение классической модели регрессии (RandomForestRegressor) и сохранение в joblib.
"""
from __future__ import annotations

import argparse
import configparser
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from .logger import Logger, show_logs_from_env
from .paths import FEATURE_NAMES, ROOT


def _train_params_from_config_ini(root: Path) -> dict:
    cfg_path = root / "config.ini"
    if not cfg_path.is_file():
        return {}
    cfg = configparser.ConfigParser()
    cfg.read(cfg_path, encoding="utf-8")
    if not cfg.has_section("MODEL"):
        return {}
    sec = cfg["MODEL"]
    out: dict = {}
    if sec.get("n_estimators"):
        out["n_estimators"] = int(sec["n_estimators"])
    if "max_depth" in sec:
        raw_md = sec.get("max_depth", "").strip()
        if raw_md.lower() in ("", "none", "null"):
            out["max_depth"] = None
        else:
            out["max_depth"] = int(raw_md)
    if sec.get("random_state") is not None:
        out["random_state"] = int(sec["random_state"])
    if "n_jobs" in sec:
        out["n_jobs"] = int(sec["n_jobs"])
    return out


def _train_params_from_yaml(root: Path) -> dict:
    p = root / "params.yaml"
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("train", {}) or {}


def load_xy(proc_dir: Path):
    X_train = pd.read_csv(proc_dir / "X_train.csv")
    X_test = pd.read_csv(proc_dir / "X_test.csv")
    y_train = pd.read_csv(proc_dir / "y_train.csv").squeeze("columns")
    y_test = pd.read_csv(proc_dir / "y_test.csv").squeeze("columns")
    return X_train, X_test, y_train, y_test


def run_train(
    root: Path | None = None,
    n_estimators: int | None = None,
    max_depth: int | None = None,
    random_state: int | None = None,
    n_jobs: int | str | None = None,
) -> dict[str, float]:
    root = root or ROOT
    log = Logger(show_logs_from_env()).get_logger(__name__)
    # Приоритет: CLI > config.ini > params.yaml (legacy train:) > значения по умолчанию
    ini_params = _train_params_from_config_ini(root)
    yaml_params = _train_params_from_yaml(root)
    merged = {**yaml_params, **ini_params}
    n_estimators = int(n_estimators if n_estimators is not None else merged.get("n_estimators", 100))
    if max_depth is not None:
        max_depth = int(max_depth)
    else:
        md = merged.get("max_depth", 12)
        max_depth = int(md) if md is not None else None
    random_state = int(random_state if random_state is not None else merged.get("random_state", 42))
    if n_jobs is None:
        n_jobs = merged.get("n_jobs", -1)
    log.info(
        "train: n_estimators=%s max_depth=%s random_state=%s n_jobs=%s",
        n_estimators,
        max_depth,
        random_state,
        n_jobs,
    )

    proc_dir = root / "data" / "processed"
    model_path = root / "models" / "model.joblib"
    (root / "models").mkdir(parents=True, exist_ok=True)

    X_train, X_test, y_train, y_test = load_xy(proc_dir)
    for col in FEATURE_NAMES:
        if col not in X_train.columns:
            raise ValueError(f"Отсутствует признак {col}")

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    metrics = {
        "r2": float(r2_score(y_test, pred)),
        "mae": float(mean_absolute_error(y_test, pred)),
    }
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, model_path)
    log.info("train: метрики %s, модель %s", metrics, model_path)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Обучение RandomForestRegressor")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--n-estimators", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    args = parser.parse_args()
    metrics = run_train(
        root=args.root,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state,
    )
    print("Метрики на тесте:", metrics)


if __name__ == "__main__":
    main()
