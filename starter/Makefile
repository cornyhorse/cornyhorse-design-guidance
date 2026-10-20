.PHONY: build up down test cov integration migrate makemigrations shell createsuperuser logs sprite

build:
	docker compose --profile test build

up:
	docker compose up

down:
	docker compose down

# Unit tests (fast, no broker). Coverage is enforced at 100% by `make cov` and CI.
test:
	docker compose run --rm test pytest $(ARGS)

cov:
	docker compose run --rm test pytest --cov --cov-report=term-missing $(ARGS)

# Round trip through the real broker and a running worker.
integration:
	docker compose run --rm web python3 manage.py migrate
	docker compose up -d worker
	docker compose run --rm test pytest -m integration $(ARGS)

migrate:
	docker compose run --rm web python3 manage.py migrate

makemigrations:
	docker compose run --rm web python3 manage.py makemigrations $(ARGS)

shell:
	docker compose run --rm web python3 manage.py shell

createsuperuser:
	docker compose run --rm web python3 manage.py createsuperuser

logs:
	docker compose logs -f $(ARGS)

# Rebuild static/vendor/bootstrap-icons/sprite.svg after adding or removing an icon.
sprite:
	python3 scripts/build_icon_sprite.py
