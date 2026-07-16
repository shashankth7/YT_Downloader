.PHONY: setup dev prod_up prod_down build

setup:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

dev:
	python backend/app.py

prod_up:
	docker compose -f docker-compose.prod.yml up -d --build

prod_down:
	docker compose -f docker-compose.prod.yml down

build:
	docker compose -f docker-compose.prod.yml build
