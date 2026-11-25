import re

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from model import Response, trim, valid_name, whole_number


def problem(status, code):
    return Response(status, {"error": code})


def view(item):
    return {
        "id": str(item["_id"]),
        "owner": item["owner"],
        "sku": item["sku"],
        "name": item["name"],
        "quantity": item["quantity"],
        "version": item["version"],
    }


class InventoryService:
    def __init__(self, collection):
        self.collection = collection

    def handle(self, method, path, user, body=None):
        if not isinstance(user, str) or not trim(user):
            return problem(401, "unauthorized")

        match = re.fullmatch(r"/items/([^/]+)", path)
        if path != "/items" and match is None:
            return problem(404, "not_found")

        # owner goes in every query, so nobody can touch someone else's items
        query = {"owner": user}
        if match:
            if not re.fullmatch(r"[0-9a-fA-F]{24}", match[1]):
                return problem(400, "invalid_id")
            query["_id"] = ObjectId(match[1])

        try:
            if path == "/items" and method == "POST":
                if not isinstance(body, dict) or set(body) != {
                    "sku",
                    "name",
                    "quantity",
                }:
                    return problem(400, "invalid_input")
                sku = body["sku"]
                name = valid_name(body["name"])
                quantity = whole_number(body["quantity"], 0, 1000000)
                if (
                    not isinstance(sku, str)
                    or not re.fullmatch(r"[A-Z0-9-]{1,24}", sku)
                    or name is None
                    or quantity is None
                ):
                    return problem(400, "invalid_input")
                item = {
                    "_id": ObjectId(),
                    "owner": user,
                    "sku": sku,
                    "name": name,
                    "quantity": quantity,
                    "version": 1,
                }
                self.collection.insert_one(item)
                return Response(201, view(item))

            if path == "/items" and method == "GET":
                items = self.collection.find(query).sort([("sku", 1), ("_id", 1)])
                return Response(200, [view(item) for item in items])

            if match and method == "GET":
                item = self.collection.find_one(query)
                if item is None:
                    return problem(404, "item_not_found")
                return Response(200, view(item))

            if match and method == "PATCH":
                if (
                    not isinstance(body, dict)
                    or set(body) - {"name", "quantity", "version"}
                    or not {"name", "quantity"} & body.keys()
                ):
                    return problem(400, "invalid_input")
                version = whole_number(body.get("version"), 1, 9223372036854775806)
                if version is None:
                    return problem(400, "invalid_input")
                patch = {}
                if "name" in body:
                    name = valid_name(body["name"])
                    if name is None:
                        return problem(400, "invalid_input")
                    patch["name"] = name
                if "quantity" in body:
                    quantity = whole_number(body["quantity"], 0, 1000000)
                    if quantity is None:
                        return problem(400, "invalid_input")
                    patch["quantity"] = quantity
                if self.collection.find_one(query) is None:
                    return problem(404, "item_not_found")
                # one atomic step: only the matching version gets updated,
                # so two patches on the same version can't both win
                updated = self.collection.find_one_and_update(
                    {**query, "version": version},
                    {"$set": patch, "$inc": {"version": 1}},
                    return_document=ReturnDocument.AFTER,
                )
                if updated is None:
                    return problem(409, "version_conflict")
                return Response(200, view(updated))

            if match and method == "DELETE":
                deleted = self.collection.delete_one(query).deleted_count
                if not deleted:
                    return problem(404, "item_not_found")
                return Response(204, None)

            return problem(405, "method_not_allowed")
        except DuplicateKeyError:
            return problem(409, "sku_conflict")
        except OperationFailure as error:
            if error.code == 121:
                return problem(400, "invalid_input")
            return problem(503, "storage_unavailable")
        except PyMongoError:
            return problem(503, "storage_unavailable")
