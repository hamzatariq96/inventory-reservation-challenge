# Challenge: Inventory Reservation Service

**Time guide:** 2–3 hours  
**Stack:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16 (all provided through Docker)

## Background

An online store lets customers put items in their cart before paying. While a
customer is checking out, the items should be held for them so nobody else can
buy the last unit. If the customer does not finish in time, the hold should lapse
and the stock should become available again.

You are implementing the rules behind that hold. The HTTP layer, database models
and test suite already exist. Your work goes in `backend/app/services.py`.

## Getting started

```bash
cp starter/app/services.py backend/app/services.py   # skip if you received the starter already
make up                # app on http://localhost:8080, API docs on http://localhost:8000/docs
make test-backend      # runs the grading suite against PostgreSQL
```

You only need Docker. Nothing needs to be installed on your machine.

## Requirements

### Availability

`available = total_stock − confirmed quantity − quantity of active, unexpired reservations`

Released and expired reservations do not hold stock.

### Reserving — `POST /reservations`

```json
{ "product_id": 1, "quantity": 3, "idempotency_key": "checkout-7f3a…" }
```

| Situation | Response |
|---|---|
| Enough stock | `201`, reservation with `status: "active"` and `expires_at = created_at + TTL` |
| Not enough stock | `409`, `{"detail": "only N unit(s) available"}` |
| Unknown product | `404` |
| Same `idempotency_key` and same body as an earlier call | `200`, the **original** reservation. No extra stock is held. |
| Same `idempotency_key`, different body | `409` |

Clients retry on network errors, so the idempotency rule matters: a retry must
never hold stock twice.

### Expiry

A reservation is `expired` from the instant `now >= expires_at`. There is no
background job. Expiry has to be worked out whenever a reservation or product
is read. Always read the time from the injected `Clock`, never from
`datetime.now()`.

### Confirm — `POST /reservations/{id}/confirm`

- `active` → `confirmed`. A confirmed reservation holds its stock permanently.
- Confirming an already confirmed reservation returns it unchanged (`200`).
- Expired → `409` with `{"detail": "reservation has expired"}`.
- Released → `409`.

### Release — `POST /reservations/{id}/release`

- `active` → `released`, and the stock is available again straight away.
- Releasing twice is fine (`200`).
- Confirmed → `409`.

### Concurrency

Twenty parallel requests for one unit each, against a product with five in
stock, must produce exactly five reservations. `tests/test_concurrency.py`
checks this on PostgreSQL.

## How it is graded

1. **Correctness:** `make test-backend` passes, including the concurrency test.
   The suite is deterministic: it uses a fixed clock and a fresh schema for each
   test, so a failure always points to a real bug, never to timing.
2. **Code quality:** clear names, small functions, no copy-pasted rules.
3. **Reasoning:** a short `NOTES.md` covering how you prevent overselling and
   what you would change for production traffic.

Do not modify the tests, `main.py` or `models.py`. If you think a requirement is
ambiguous, write down the assumption you made in `NOTES.md`.
