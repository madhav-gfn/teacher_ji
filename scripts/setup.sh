#!/usr/bin/env bash
set -euo pipefail

cp .env.example .env
docker-compose up -d postgres redis
sleep 5
./scripts/ingest_all.sh
docker-compose up -d api frontend
