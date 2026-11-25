# Stockroom — fixed inventory service

Fixed `service.py` for the LeetCode Stockroom project (MongoDB inventory API).

## What was broken (5 bugs)

1. Creates never saved — the code returned 201 without calling `insert_one`.
2. Bad quantity silently became 0 — `whole_number(...) or 0` hid invalid input.
3. No owner check — any user could read, update or delete anyone else's items.
4. PATCH returned stale data — `ReturnDocument.BEFORE` gave back old values.
5. Duplicate SKU gave 503 — mapped to `storage_unavailable` instead of 409.

## Run the tests

Needs Python 3.11+, PyMongo 4.11.3 and MongoDB 8.0 running at
`mongodb://127.0.0.1:27017` (set `MONGODB_URI` if yours is elsewhere).

```bash
pip install pymongo==4.11.3
python -m unittest test_client test_regression
```

## Run the demo server

```bash
bash .theia/run_app.sh
# or: PORT=8080 python server.py
```

## Files

- `service.py` — the repaired service (only file you need to paste into the IDE)
- `model.py`, `server.py` — fixed files, unchanged
- `test_support.py`, `test_client.py` — public test fixtures and smoke checks
- `test_regression.py` — 10 extra checks for the five bugs
