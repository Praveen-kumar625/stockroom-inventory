"""Isolated MongoDB fixtures shared by public and author tests."""

import os
import unittest
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient

from model import Response, initialize_items
from service import InventoryService


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        self.client = MongoClient(
            os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"),
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
        )
        self.client.admin.command("ping")
        self.database_name = "stockroom_test_" + uuid4().hex
        self.addCleanup(self.client.close)
        self.addCleanup(self.client.drop_database, self.database_name)
        self.collection = initialize_items(self.client[self.database_name])
        self.service = InventoryService(self.collection)

    def post(self, user="u", sku="ABC", **values):
        return self.service.handle(
            "POST",
            "/items",
            user,
            {"sku": sku, "name": " Widget ", "quantity": 3, **values},
        )

    def seed(self, user="u", sku="SEED"):
        item = {
            "_id": ObjectId(),
            "owner": user,
            "sku": sku,
            "name": "Seed",
            "quantity": 3,
            "version": 1,
        }
        self.collection.insert_one(item)
        return "/items/" + str(item["_id"])

    def error(self, status, code):
        return Response(status, {"error": code})
