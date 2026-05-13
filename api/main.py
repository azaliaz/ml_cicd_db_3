"""
FastAPI: метод предсказания медианной стоимости жилья (California Housing, регрессия).
Запуск из корня проекта: uvicorn api.main:app --reload
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from logger import Logger, show_logs_from_env  # noqa: E402
from paths import FEATURE_NAMES, MODEL_PATH  # noqa: E402
from db import init_db, save_prediction  # noqa: E402

_LOG = Logger(show_logs_from_env()).get_logger(__name__)

app = FastAPI(title="California Housing API", version="1.0.0")

_model_cache: dict[str, dict] = {}


def get_model_path() -> Path:
    override = os.environ.get("MODEL_PATH")
    return Path(override) if override else MODEL_PATH


def load_bundle() -> dict:
    path = get_model_path().resolve()
    key = str(path)
    if key not in _model_cache:
        if not path.is_file():
            raise FileNotFoundError(
                f"Модель не найдена: {path}. Выполните: python -m src.preprocess && python -m src.train"
            )
        _LOG.info("load_bundle: загрузка модели из %s", path)
        _model_cache[key] = joblib.load(path)
    return _model_cache[key]


class PredictRequest(BaseModel):
    """Вектор признаков в том же порядке, что и в sklearn California Housing."""

    MedInc: float = Field(..., description="Медианный доход в блоке")
    HouseAge: float = Field(..., description="Медианный возраст домов")
    AveRooms: float = Field(..., description="Среднее число комнат")
    AveBedrms: float = Field(..., description="Среднее число спален")
    Population: float = Field(..., description="Население блока")
    AveOccup: float = Field(..., description="Средняя занятость жилья")
    Latitude: float = Field(..., ge=32, le=43, description="Широта")
    Longitude: float = Field(..., ge=-125, le=-114, description="Долгота")


class PredictResponse(BaseModel):
    median_house_value: float = Field(..., description="Предсказанная медианная стоимость, $100k")
    prediction_id: int = Field(..., description="ID записи предсказания в базе данных")


@app.get("/health")
def health():
    _LOG.debug("health check")
    return {"status": "ok"}


@app.on_event("startup")
def startup() -> None:
    init_db()
    _LOG.info("startup: db initialized")


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest):
    bundle = load_bundle()
    model = bundle["model"]
    names: list[str] = bundle.get("feature_names", FEATURE_NAMES)
    features = {name: float(getattr(body, name)) for name in names}
    X_df = pd.DataFrame([[features[name] for name in names]], columns=names)
    try:
        value = float(model.predict(X_df)[0])
    except Exception as e:
        _LOG.exception("predict: ошибка инференса")
        raise HTTPException(status_code=400, detail=str(e)) from e
    prediction_id = save_prediction(features=features, prediction_value=value, model_path=get_model_path())
    _LOG.info("predict: ok median_house_value=%s prediction_id=%s", value, prediction_id)
    return PredictResponse(median_house_value=value, prediction_id=prediction_id)


