.PHONY: up down logs api-shell db-migration db-upgrade

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api-shell:
	docker compose exec api sh

db-migration:
	docker compose exec api sh -c 'cd /app && alembic -c /src/apps/api/alembic.ini revision --autogenerate -m "$(m)"'

db-upgrade:
	docker compose exec api alembic upgrade head
