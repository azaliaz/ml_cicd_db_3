from pathlib import Path

import yaml

from src.preprocess import run_preprocess
from src.train import run_train

from tests.helpers import write_minimal_config_ini, write_tiny_california_housing_csv


def test_train_produces_model_and_metrics(tmp_path: Path):
    params = {"preprocess": {"test_size": 0.3, "random_state": 0}}
    (tmp_path / "params.yaml").write_text(yaml.safe_dump(params), encoding="utf-8")
    write_minimal_config_ini(tmp_path, n_estimators=20, max_depth=4, random_state=0, n_jobs=2)
    write_tiny_california_housing_csv(tmp_path)
    run_preprocess(root=tmp_path)
    metrics = run_train(root=tmp_path)
    assert "r2" in metrics and "mae" in metrics
    assert (tmp_path / "models" / "model.joblib").is_file()
