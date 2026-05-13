from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.preprocess import run_preprocess
from src.train import run_train

from tests.helpers import write_minimal_config_ini, write_tiny_california_housing_csv


def test_health():
    import api.main as api_main

    api_main._model_cache.clear()
    api_main.init_db = lambda: None
    client = TestClient(api_main.app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_returns_value(tmp_path: Path, monkeypatch):
    params = {"preprocess": {"test_size": 0.3, "random_state": 1}}
    (tmp_path / "params.yaml").write_text(yaml.safe_dump(params), encoding="utf-8")
    write_minimal_config_ini(tmp_path, n_estimators=15, max_depth=6, random_state=1, n_jobs=2)
    write_tiny_california_housing_csv(tmp_path)
    run_preprocess(root=tmp_path)
    run_train(root=tmp_path)
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "models" / "model.joblib"))

    import api.main as api_main

    api_main._model_cache.clear()
    api_main.init_db = lambda: None
    saved_rows: list[dict] = []

    def _fake_save_prediction(*, features, prediction_value, model_path):
        saved_rows.append(
            {
                "features": features,
                "prediction_value": prediction_value,
                "model_path": str(model_path),
            }
        )
        return 1

    api_main.save_prediction = _fake_save_prediction

    payload = {
        "MedInc": 8.3252,
        "HouseAge": 41.0,
        "AveRooms": 6.984127,
        "AveBedrms": 1.02381,
        "Population": 322.0,
        "AveOccup": 2.555556,
        "Latitude": 37.88,
        "Longitude": -122.23,
    }
    client = TestClient(api_main.app)
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "median_house_value" in body
    assert "prediction_id" in body
    assert isinstance(body["prediction_id"], int)
    assert isinstance(body["median_house_value"], (int, float))
    assert len(saved_rows) == 1
    assert isinstance(saved_rows[0]["prediction_value"], float)
