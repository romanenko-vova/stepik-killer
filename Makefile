# Локальная разработка: make db && make migrate && make run

db: ## поднять Postgres в docker (127.0.0.1:5434)
	docker compose up -d db

migrate: ## накатить миграции
	.venv/bin/python -m alembic upgrade head

migration: ## новая миграция: make migration MESSAGE="что меняем"
	.venv/bin/python -m alembic revision -m "$(MESSAGE)"

run: ## бот с перезапуском при правке файлов
	watchfiles --filter python --ignore-path .venv,__pycache__ ".venv/bin/python main.py"

test: ## все тесты (нужны docker и Postgres)
	.venv/bin/python -m pytest -q

catalog: ## эталоны против всех тестов каталога
	.venv/bin/python -m scripts.check_catalog

.PHONY: db migrate migration run test catalog
