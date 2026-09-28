# Architecture

```
browser ──> web (nginx) ──/api──> api (FastAPI) ──> db (PostgreSQL 16)
             :8080                  :8000
```

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | App factory, routing, dependency wiring, error → HTTP mapping |
| `backend/app/services.py` | All reservation rules. No FastAPI imports, so it can be tested on its own |
| `backend/app/models.py` | SQLAlchemy tables and DB-level constraints |
| `backend/app/clock.py` | `SystemClock` for production, `FixedClock` for tests |
| `frontend/src/lib/stock.ts` | Pure UI logic (countdown, status, validation) with `now` passed in |
| `frontend/src/App.tsx` | UI state and API calls |

## Decisions

**Lazy expiry instead of a background job.** A reservation's status is worked
out when it is read (`effective_status`), and the availability query simply
ignores holds whose `expires_at` has passed. This removes a moving part and
means nothing depends on a scheduler running on time.

**Row lock on the product.** `reserve` selects the product with
`SELECT … FOR UPDATE` before checking availability. Two concurrent requests for
the same product are forced to run one after the other, so the check and the
insert behave as one step. Requests for different products do not block each
other.

**Idempotency key with a unique constraint.** The lookup handles normal
retries. The unique constraint handles two identical requests arriving at the
same moment: the loser gets an `IntegrityError`, rolls back and returns the
winner's reservation.

**Injected clock.** Business logic never calls `datetime.now()`. Tests move a
`FixedClock` forward by exact amounts, for example to one second before the TTL
and then exactly to it. That makes the boundary tests exact and removes the
need for `sleep`.

**Naive UTC timestamps.** They compare the same way on PostgreSQL and SQLite.
The frontend parses them as UTC explicitly, and its tests pass under any `TZ`.

## Why the tests are deterministic

- A fixed start time and an injected clock are used. Nothing in the tests reads the real time.
- Each test gets a new schema (`create_all` / `drop_all`), so test order does not matter.
- There is no randomness and there are no network calls. IDs come from the database sequence of a fresh table.
- The concurrency test asserts an outcome that holds for every thread interleaving: exactly `stock` successes.
- Everything runs in pinned Docker images (`python:3.12-slim`, `node:20-alpine`, `postgres:16-alpine`) with pinned dependencies and a lockfile.
