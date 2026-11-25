# Stockroom Inventory API

A fixed MongoDB inventory API. This was a LeetCode debugging project. The starter code had five bugs. I found them and fixed them in `service.py` only.

## Problem statement

There is a small inventory service. It stores items in MongoDB and serves them over HTTP. Each user owns their own items. The service must do this:

- Create an item with a SKU, name and quantity. The SKU must be unique for each owner.
- List only the logged in user's items, sorted by SKU.
- Read, update and delete one item by its id.
- Updates use optimistic locking. Each item has a version number. A PATCH must carry the current version, or it fails with 409.
- Every error must be a plain `{"error": "code"}` body with the right status code. No stack traces, no extra fields.

The starter code looked fine at first glance, but five bugs were hiding in it.

## Approach

I worked in small steps.

1. Read the full spec first. The rules for auth, routes, ids, validation and errors are strict, so I made sure I understood them before touching code.
2. Ran the public tests to see what fails.
3. Read `service.py` line by line and matched each line against the spec.
4. Fixed one bug at a time and re-ran the tests after each fix.
5. Wrote 10 extra regression tests for the five bugs, including a 10-thread concurrency test for PATCH.
6. Ran the real server once over HTTP to check the full flow.

I did not change `model.py` or `server.py`. Those were fixed files. Only `service.py` and the reflection file were mine to edit.

## What was broken, and what I fixed

1. Creates never saved. POST built the item dict and returned 201, but the insert was a bare `pass`. Nothing reached the database. Fix: call `insert_one` and return what the database holds.
2. Bad quantity silently became 0. `whole_number(...) or 0` turned invalid input into a quiet 0. Fix: keep the None check and reject bad input with 400.
3. No owner check. Queries carried only the item id, and the list query was empty. Any user could read, update or delete anyone else's items. Fix: every query starts with the owner.
4. PATCH returned stale data. It used `ReturnDocument.BEFORE`, so the client got the old values back. Fix: return the document after the update.
5. Duplicate SKU gave 503. A duplicate key error was mapped to `storage_unavailable`. Fix: map error 11000 to 409 `sku_conflict`. The unique index on (owner, sku) does the real work here, and it works across service instances because it lives in the database, not in app memory.

## Test results

13 out of 13 tests pass. 3 public tests and 10 regression tests.

- All five bugs have a test that fails on the starter code and passes on the fix.
- The concurrency test runs 10 PATCH requests on the same version at the same time. Exactly one succeeds with 200. The other nine get 409. The final version is 2.

Tests run against a real MongoDB 8.0, not a mock.

## How to run

You need Python 3.11 or later, PyMongo 4.11.3, and MongoDB 8.0 running on `mongodb://127.0.0.1:27017`. Set `MONGODB_URI` if yours is elsewhere.

```bash
pip install pymongo==4.11.3
python -m unittest test_client test_regression
```

Demo server (default port 8080):

```bash
python server.py
```

## Files

- `service.py` — the repaired service. The only file you need to paste into the IDE.
- `model.py`, `server.py` — fixed files, unchanged.
- `test_support.py`, `test_client.py` — public test fixtures and smoke checks.
- `test_regression.py` — 10 extra checks for the five bugs.
- `REFLECTION.essay` — short answers to three questions: why uniqueness must live in the database, how building, inserting and updating a document differ, and how retry-safe adjustments differ from setting an absolute quantity.

## Notes

- Auth runs first. A missing or blank user gets 401 before anything else.
- An id must be exactly 24 hex characters, or it is 400 `invalid_id`.
- PATCH validates the whole payload before it looks the item up, so bad input is 400 even when the item does not exist.
- A duplicate SKU for the same owner is 409. Another owner can use the same SKU.
