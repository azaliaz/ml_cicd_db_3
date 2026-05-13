#!/bin/sh
set -e
cd /app
python -m src.preprocess
python -m src.train
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
