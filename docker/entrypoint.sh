#!/bin/sh
set -e
cd /app

# CD / прод: образ уже содержит model.joblib (см. Dockerfile). Локально по умолчанию — полный цикл.
if [ "${SKIP_PREPROCESS_TRAIN:-}" = "1" ] || [ "${SKIP_PREPROCESS_TRAIN:-}" = "true" ]; then
  exec uvicorn api.main:app --host 0.0.0.0 --port 8000
fi

python -m src.preprocess
python -m src.train
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
