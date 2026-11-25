"""Fixed MongoDB schema and cross-runtime value rules."""

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pymongo.errors import CollectionInvalid, OperationFailure

WHITESPACE = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


@dataclass
class Response:
    status: int
    body: Any


def initialize_items(database):
    schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["owner", "sku", "name", "quantity", "version"],
            "properties": {
                "owner": {"bsonType": "string", "minLength": 1},
                "sku": {"bsonType": "string", "pattern": "^[A-Z0-9-]{1,24}$"},
                "name": {"bsonType": "string", "minLength": 1, "maxLength": 80},
                "quantity": {
                    "bsonType": ["int", "long"],
                    "minimum": 0,
                    "maximum": 1000000,
                },
                "version": {"bsonType": ["int", "long"], "minimum": 1},
            },
        }
    }
    try:
        database.create_collection("items", validator=schema)
    except CollectionInvalid:
        pass
    except OperationFailure as error:
        if error.code != 48:
            raise
    collection = database["items"]
    collection.create_index([("owner", 1), ("sku", 1)], unique=True)
    return collection


def trim(value):
    return value.strip(WHITESPACE)


def valid_name(value):
    if not isinstance(value, str):
        return None
    name = trim(value)
    return (
        name
        if 1 <= len(name.encode("utf-16-le", errors="surrogatepass")) // 2 <= 80
        else None
    )


def whole_number(value, minimum, maximum):
    if type(value) not in (int, float, Decimal):
        return None
    if isinstance(value, float) and (
        not math.isfinite(value) or not value.is_integer()
    ):
        return None
    if isinstance(value, Decimal) and (
        not value.is_finite() or value != value.to_integral_value()
    ):
        return None
    return int(value) if minimum <= value <= maximum else None
