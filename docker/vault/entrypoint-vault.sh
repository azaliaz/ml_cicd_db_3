#!/bin/sh
# Dev-режим Vault + запись учётных данных БД в KV v2 (secret/housing/db).
# Значения сида берутся из переменных окружения контейнера (не из репозитория).
set -e
TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-housing-dev-root}"

vault server -dev \
  -dev-root-token-id="${TOKEN}" \
  -dev-listen-address=0.0.0.0:8200 &
VPID=$!

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="${TOKEN}"

i=0
while [ "$i" -lt 60 ]; do
  if vault status >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

vault kv put secret/housing/db \
  "username=${VAULT_SEED_DB_USER:?VAULT_SEED_DB_USER required}" \
  "password=${VAULT_SEED_DB_PASSWORD:?VAULT_SEED_DB_PASSWORD required}" \
  "dbname=${VAULT_SEED_DB_NAME:?VAULT_SEED_DB_NAME required}" \
  "host=${VAULT_SEED_DB_HOST:-postgres}" \
  "port=${VAULT_SEED_DB_PORT:-5432}"

wait "${VPID}"
