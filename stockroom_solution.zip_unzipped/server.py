"""Fixed HTTP transport for the inventory service."""

import json
import os
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from pymongo import MongoClient

from model import Response, initialize_items
from service import InventoryService


def reject_constant(value):
    raise ValueError(value)


def create_server(service, address=("127.0.0.1", 0)):
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 1048576:
                    raise ValueError("invalid body length")
                raw = self.rfile.read(length)
                body = (
                    json.loads(
                        raw.decode("utf-8"),
                        parse_float=Decimal,
                        parse_constant=reject_constant,
                    )
                    if raw
                    else {}
                )
            except (ValueError, UnicodeError):
                response = Response(400, {"error": "invalid_json"})
            else:
                response = service.handle(
                    self.command,
                    urlsplit(self.path).path,
                    self.headers.get("X-User-ID"),
                    body,
                )
            encoded = (
                b""
                if response.status == 204
                else json.dumps(
                    response.body, ensure_ascii=True, allow_nan=False
                ).encode()
            )
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(encoded)

        do_GET = do_POST = do_PATCH = do_DELETE = do_PUT = do_HEAD = do_OPTIONS = (
            handle_request
        )

        def __getattr__(self, name):
            if name.startswith("do_"):
                return self.handle_request
            raise AttributeError(name)

        def log_message(self, *_args):
            pass

    return ThreadingHTTPServer(address, Handler)


def main():
    client = MongoClient(
        os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=3000,
    )
    collection = initialize_items(
        client[os.environ.get("MONGODB_DATABASE", "stockroom_local")]
    )
    server = create_server(
        InventoryService(collection), ("0.0.0.0", int(os.environ.get("PORT", "8080")))
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":
    main()
