"""
FaultyStripeTransport — an httpx.AsyncBaseTransport that simulates
Stripe misbehaving at the HTTP wire level.

Injected into httpx.AsyncClient so real httpx code (connection handling,
response parsing, header processing) runs — only the socket is replaced.

Fault modes
───────────
"timeout"        httpx.ReadTimeout  — provider never responds
"connection"     httpx.ConnectError — TCP refused / DNS failure
"server_500"     HTTP 500           — Stripe internal error
"200_error_body" HTTP 200 with {"error": {"message": "processing_error"}}
"garbled"        HTTP 200 with wrong JSON shape (renamed fields)
"non_json"       HTTP 200 with plain text — not valid JSON
"""

from __future__ import annotations

import json

import httpx


class FaultyStripeTransport(httpx.AsyncBaseTransport):
    def __init__(self, fault: str) -> None:
        _valid = {"timeout", "connection", "server_500", "200_error_body", "garbled", "non_json"}
        if fault not in _valid:
            raise ValueError(f"unknown fault {fault!r}, choose from {_valid}")
        self._fault = fault

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        match self._fault:
            case "timeout":
                raise httpx.ReadTimeout("Stripe did not respond", request=request)
            case "connection":
                raise httpx.ConnectError("connection refused", request=request)
            case "server_500":
                return _json_response(500, {"error": {"message": "internal server error"}})
            case "200_error_body":
                return _json_response(200, {"error": {"message": "processing_error"}, "status": "error"})
            case "garbled":
                # Fields renamed — "id" → "charge_id", "amount" → "amt"
                return _json_response(200, {"charge_id": "ch_xyz", "amt": 1000, "curr": "eur"})
            case "non_json":
                return httpx.Response(200, content=b"<html>Bad Gateway</html>")
            case _:
                raise AssertionError(f"unhandled fault: {self._fault}")


def _json_response(status: int, body: dict) -> httpx.Response:
    content = json.dumps(body).encode()
    return httpx.Response(
        status,
        content=content,
        headers={"content-type": "application/json"},
    )
