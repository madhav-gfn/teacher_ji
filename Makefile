.PHONY: setup ingest dev prod down test logs

setup:
	cp .env.example .env
	docker-compose up -d postgres redis
	sleep 5
	$(MAKE) ingest
	docker-compose up -d api frontend

ingest:
	docker-compose run --rm api python rag/ingest.py --subject math --grade 6 --pdf_dir /app/data/ncert/class6/math/
	docker-compose run --rm api python rag/ingest.py --subject science --grade 6 --pdf_dir /app/data/ncert/class6/science/
	docker-compose run --rm api python rag/ingest.py --subject sst --grade 6 --pdf_dir /app/data/ncert/class6/sst/

dev:
	docker-compose up

prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down:
	docker-compose down

test:
	python scripts/test_e2e.py

logs:
	docker-compose logs -f api
