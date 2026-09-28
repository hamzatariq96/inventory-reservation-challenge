# Inventory Reservation Service

A small full-stack app that holds stock for a customer during checkout and
releases it if they don't finish in time. It is also packaged as a **coding
challenge**, with a written spec, a starter file and a deterministic grading
suite.

**Stack:** React + TypeScript (Vite) · FastAPI · SQLAlchemy · PostgreSQL · Docker Compose · Pytest · Jest

## Run it

You only need Docker.

```bash
make up          # web → http://localhost:8080, API docs → http://localhost:8000/docs
make test        # Pytest (against PostgreSQL) + Jest, both inside containers
make down        # stop and remove the database volume
```

Without `make`:

```bash
docker compose up --build -d
docker compose --profile test run --rm backend-tests
docker compose --profile test run --rm frontend-tests
```

## What it does

- Create products with a fixed amount of stock.
- Reserve units. A reservation holds stock for 10 minutes (`RESERVATION_TTL_SECONDS`).
- Confirm a reservation to keep the stock, or release it to give the stock back.
- Unconfirmed reservations expire on their own and the stock becomes available again.
- Retries are safe: every reservation request carries an idempotency key.
- It does not oversell under concurrent requests. A test covers this.

## Project layout

```
backend/            FastAPI service
  app/services.py   reservation rules (the part candidates implement)
  tests/            24 Pytest tests, including a PostgreSQL concurrency test
frontend/           React UI, served by nginx in Docker
  src/lib/          pure logic + Jest tests
starter/            stubbed services.py handed to candidates
db/init.sql         creates the separate test database
docs/               architecture notes and design decisions
CHALLENGE.md        the task as a candidate receives it
```

## Using it as a challenge

```bash
cp starter/app/services.py backend/app/services.py
```

The app still starts, but the reservation logic now raises `NotImplementedError`
and the test suite fails. A candidate implements `services.py` until
`make test-backend` passes. [CHALLENGE.md](CHALLENGE.md) has the full spec and
grading criteria.

## Testing approach

The suites are written to give the same result on every machine and every run:

- **Fixed clock.** Expiry is tested at exactly one second before and exactly at the TTL, with no `sleep`.
- **Fresh schema per test.** Tests can run in any order.
- **Same database as production.** In Docker and CI, Pytest runs against PostgreSQL. Locally it falls back to in-memory SQLite.
- **Concurrency.** 20 parallel requests against 5 units must produce exactly 5 reservations. Without the row lock this test fails.
- **Timezone-safe frontend.** Jest tests pass under any `TZ`.

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) explains the design decisions.

## Local development without Docker

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                               # SQLite
uvicorn app.main:create_app --factory --reload       # http://localhost:8000

# frontend (proxies /api to localhost:8000)
cd frontend && npm ci && npm run dev
```
