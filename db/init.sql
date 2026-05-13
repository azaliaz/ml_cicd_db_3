CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    features_json JSONB NOT NULL,
    prediction_value DOUBLE PRECISION NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok'
);
