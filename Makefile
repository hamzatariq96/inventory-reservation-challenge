.PHONY: up down test test-backend test-frontend logs

up:            ## Build and start db, api and web
	docker compose up --build -d
	@echo "Web: http://localhost:8080   API docs: http://localhost:8000/docs"

down:          ## Stop everything and delete the database volume
	docker compose down -v

test: test-backend test-frontend

test-backend:  ## Pytest against PostgreSQL (includes the concurrency test)
	docker compose --profile test run --rm --build backend-tests

test-frontend: ## Jest
	docker compose --profile test run --rm --build frontend-tests

logs:
	docker compose logs -f api
