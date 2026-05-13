from pathlib import Path

from src.preprocess import run_preprocess

from tests.helpers import write_tiny_california_housing_csv


def test_preprocess_creates_files(tmp_path: Path):
    write_tiny_california_housing_csv(tmp_path)
    run_preprocess(root=tmp_path)
    assert (tmp_path / "data" / "raw" / "california_housing.csv").is_file()
    for name in ("X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv"):
        assert (tmp_path / "data" / "processed" / name).is_file()
