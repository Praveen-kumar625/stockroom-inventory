"""Regression checks for the five bugs in the starter service."""

import threading
from decimal import Decimal

from bson import ObjectId

from test_support import DatabaseCase


class RegressionTests(DatabaseCase):
    def test_create_persists(self):
        """A 201 create must survive a fresh read (bug: never inserted)."""
        created = self.post()
        self.assertEqual(created.status, 201)
        stored = self.collection.find_one({"_id": ObjectId(created.body["id"])})
        self.assertIsNotNone(stored)
        got = self.service.handle("GET", "/items/" + created.body["id"], "u")
        self.assertEqual(got.status, 200)
        self.assertEqual(got.body, created.body)

    def test_bad_quantity_rejected(self):
        """Invalid quantities are 400, not silently stored as 0."""
        for bad in (-1, 1000001, 3.5, "3", True, None, Decimal("3.5")):
            resp = self.post(quantity=bad)
            self.assertEqual(resp, self.error(400, "invalid_input"), bad)
        self.assertEqual(self.collection.count_documents({}), 0)

    def test_list_is_owner_scoped(self):
        """GET /items shows only the caller's items."""
        self.post(user="alice", sku="A1")
        self.post(user="bob", sku="A1")
        mine = self.service.handle("GET", "/items", "alice")
        self.assertEqual(len(mine.body), 1)
        self.assertEqual(mine.body[0]["owner"], "alice")

    def test_patch_returns_updated_doc(self):
        """PATCH returns new values and version+1, not the stale doc."""
        created = self.post()
        patched = self.service.handle(
            "PATCH",
            "/items/" + created.body["id"],
            "u",
            {"name": "New name", "quantity": 9, "version": 1},
        )
        self.assertEqual(patched.status, 200)
        self.assertEqual(patched.body["name"], "New name")
        self.assertEqual(patched.body["quantity"], 9)
        self.assertEqual(patched.body["version"], 2)

    def test_patch_version_conflict(self):
        """A second patch on the same version gets 409."""
        created = self.post()
        path = "/items/" + created.body["id"]
        first = self.service.handle(
            "PATCH", path, "u", {"quantity": 5, "version": 1}
        )
        self.assertEqual(first.status, 200)
        second = self.service.handle(
            "PATCH", path, "u", {"quantity": 6, "version": 1}
        )
        self.assertEqual(second, self.error(409, "version_conflict"))
        # failed update changed nothing
        kept = self.service.handle("GET", path, "u").body
        self.assertEqual(kept["quantity"], 5)
        self.assertEqual(kept["version"], 2)

    def test_concurrent_patch_one_winner(self):
        """Ten threads patching version 1: exactly one succeeds."""
        created = self.post()
        path = "/items/" + created.body["id"]
        results = []

        def patch_one(n):
            results.append(
                self.service.handle(
                    "PATCH", path, "u", {"quantity": n, "version": 1}
                ).status
            )

        threads = [threading.Thread(target=patch_one, args=(n,)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count(409), 9)
        self.assertEqual(self.service.handle("GET", path, "u").body["version"], 2)

    def test_duplicate_sku_conflict(self):
        """Same owner + same sku is 409; another owner may reuse it."""
        self.assertEqual(self.post().status, 201)
        self.assertEqual(self.post(), self.error(409, "sku_conflict"))
        self.assertEqual(self.post(user="other").status, 201)
        self.assertEqual(self.collection.count_documents({}), 2)

    def test_delete_is_owner_scoped(self):
        """Only the owner can delete; a repeat delete is 404."""
        path = self.seed(user="alice")
        self.assertEqual(
            self.service.handle("DELETE", path, "bob"),
            self.error(404, "item_not_found"),
        )
        self.assertEqual(self.service.handle("DELETE", path, "alice").status, 204)
        self.assertEqual(
            self.service.handle("DELETE", path, "alice"),
            self.error(404, "item_not_found"),
        )

    def test_patch_validates_before_lookup(self):
        """Bad payload is 400 even when the item does not exist."""
        resp = self.service.handle(
            "PATCH",
            "/items/" + "0" * 24,
            "u",
            {"quantity": -1, "version": 1},
        )
        self.assertEqual(resp, self.error(400, "invalid_input"))

    def test_bad_id_and_unknown_route(self):
        """Short ids are 400; unknown paths are 404."""
        self.assertEqual(
            self.service.handle("GET", "/items/abc", "u"),
            self.error(400, "invalid_id"),
        )
        self.assertEqual(
            self.service.handle("GET", "/nope", "u"), self.error(404, "not_found")
        )
