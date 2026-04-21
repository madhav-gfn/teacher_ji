#!/usr/bin/env bash
set -euo pipefail

docker-compose run --rm api python rag/ingest.py --subject math --grade 6 --pdf_dir /app/data/ncert/class6/math/
docker-compose run --rm api python rag/ingest.py --subject science --grade 6 --pdf_dir /app/data/ncert/class6/science/
docker-compose run --rm api python rag/ingest.py --subject sst --grade 6 --pdf_dir /app/data/ncert/class6/sst/
