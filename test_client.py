"""Public smoke checks; the full statement remains the required contract."""

from test_support import DatabaseCase


class PublicTests(DatabaseCase):
    def test_authentication(self):
        """Blank identity is rejected before accessing inventory."""
        self.assertEqual(
            self.service.handle("GET", "/items", ""), self.error(401, "unauthorized")
        )

    def test_create_and_read(self):
        """A successful creation survives a later lookup."""
        created = self.post()
        self.assertEqual(created.status, 201)
        self.assertEqual(
            self.service.handle("GET", "/items/" + created.body["id"], "u").body,
            created.body,
        )

    def test_owner_isolation(self):
        """Another user cannot read an existing private item."""
        self.assertEqual(
            self.service.handle("GET", self.seed(), "other"),
            self.error(404, "item_not_found"),
        )
