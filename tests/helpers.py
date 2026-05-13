"""Синтетический датасет для тестов без скачивания из сети."""
from pathlib import Path

import numpy as np
import pandas as pd

from src.paths import FEATURE_NAMES, TARGET_NAME


def write_minimal_config_ini(
    root: Path,
    *,
    n_estimators: int = 20,
    max_depth: int = 6,
    random_state: int = 1,
    n_jobs: int = 2,
) -> None:
    text = (
        "[MODEL]\n"
        f"n_estimators = {n_estimators}\n"
        f"max_depth = {max_depth}\n"
        f"random_state = {random_state}\n"
        f"n_jobs = {n_jobs}\n"
    )
    (root / "config.ini").write_text(text, encoding="utf-8")


def write_tiny_california_housing_csv(root: Path, n: int = 160, seed: int = 0) -> None:
    raw = root / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "MedInc": rng.uniform(1.0, 12.0, n),
            "HouseAge": rng.uniform(1.0, 52.0, n),
            "AveRooms": rng.uniform(2.0, 10.0, n),
            "AveBedrms": rng.uniform(0.8, 3.0, n),
            "Population": rng.uniform(100.0, 4000.0, n),
            "AveOccup": rng.uniform(1.0, 6.0, n),
            "Latitude": rng.uniform(32.5, 42.0, n),
            "Longitude": rng.uniform(-124.5, -114.0, n),
            TARGET_NAME: rng.uniform(0.5, 5.5, n),
        }
    )
    for col in FEATURE_NAMES:
        if col not in df.columns:
            raise RuntimeError(col)
    df.to_csv(raw / "california_housing.csv", index=False)
