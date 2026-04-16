#!/usr/bin/env python3
"""Zadarma REST API client and CLI for Hermes telephony-zadarma skill.

Implements HMAC-SHA1 signed requests per Zadarma docs:
  https://zadarma.com/en/support/api/
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

API_BASE = "https://api.zadarma.com"
ENV_PATH = Path.home() / ".hermes" / ".env"


def _sign(method_path: str, params: dict[str, Any], secret: str) -> str:
    """Build the Zadarma Authorization signature.

    Algorithm: base64( hmac_sha1( secret, method_path + sorted_qs + md5(sorted_qs) ) )
    """
    sorted_qs = urlencode(sorted(params.items()))
    md5_qs = hashlib.md5(sorted_qs.encode()).hexdigest()
    payload = f"{method_path}{sorted_qs}{md5_qs}".encode()
    digest = hmac.new(secret.encode(), payload, hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _request(method_path: str, params: dict[str, Any] | None = None,
             http_method: str = "GET") -> dict[str, Any]:
    params = params or {}
    key = os.environ.get("ZADARMA_KEY")
    secret = os.environ.get("ZADARMA_SECRET")
    if not key or not secret:
        raise RuntimeError(
            "Missing ZADARMA_KEY / ZADARMA_SECRET. Set them in ~/.hermes/.env "
            "or run `python zadarma.py save-creds --key ... --secret ...`."
        )

    signature = _sign(method_path, params, secret)
    headers = {"Authorization": f"{key}:{signature}"}
    url = API_BASE + method_path
    qs = urlencode(sorted(params.items()))

    if http_method == "GET":
        resp = requests.get(f"{url}?{qs}" if qs else url, headers=headers, timeout=15)
    else:
        resp = requests.request(http_method, url, data=params, headers=headers, timeout=15)

    try:
        return resp.json()
    except ValueError:
        return {"status": "error", "http_status": resp.status_code, "body": resp.text}


# --- Public API -----------------------------------------------------------

def balance() -> dict[str, Any]:
    return _request("/v1/info/balance/")


def numbers() -> dict[str, Any]:
    return _request("/v1/direct_numbers/")


def callback(to: str, from_: str | None = None,
             predicted: bool = False, sip: str | None = None) -> dict[str, Any]:
    """Place a bridged callback. Zadarma rings `from_` first, then `to`, then bridges."""
    src = from_ or os.environ.get("ZADARMA_FROM")
    if not src:
        raise RuntimeError("Missing source: pass --from or set ZADARMA_FROM.")
    params: dict[str, Any] = {"from": src, "to": to}
    if predicted:
        params["predicted"] = "1"
    if sip:
        params["sip"] = sip
    return _request("/v1/request/callback/", params)


def cdr(start: str, end: str) -> dict[str, Any]:
    """Call Detail Records for a UTC date range (YYYY-MM-DD)."""
    return _request("/v1/statistics/", {
        "start": f"{start} 00:00:00",
        "end": f"{end} 23:59:59",
    })


def send_sms(to: str, message: str, caller_id: str | None = None) -> dict[str, Any]:
    """Send SMS. Note: Zadarma SMS sending is region-restricted; verify destination support."""
    params: dict[str, Any] = {"number": to, "message": message}
    if caller_id:
        params["caller_id"] = caller_id
    return _request("/v1/sms/send/", params, http_method="POST")


# --- Credential persistence -----------------------------------------------

def save_creds(key: str, secret: str, default_from: str | None = None) -> None:
    """Persist creds to ~/.hermes/.env, preserving any other vars present."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing["ZADARMA_KEY"] = key
    existing["ZADARMA_SECRET"] = secret
    if default_from:
        existing["ZADARMA_FROM"] = default_from
    body = "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    ENV_PATH.write_text(body)
    ENV_PATH.chmod(0o600)
    print(f"Saved credentials to {ENV_PATH}", file=sys.stderr)


# --- CLI ------------------------------------------------------------------

def _print(obj: Any) -> None:
    json.dump(obj, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="zadarma", description="Zadarma API client for Hermes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("balance", help="Account balance")
    sub.add_parser("numbers", help="List owned numbers")

    cb = sub.add_parser("callback", help="Place a bridged callback call")
    cb.add_argument("--to", required=True, help="Destination in E.164 (e.g. +34666777888)")
    cb.add_argument("--from", dest="from_", help="Source (defaults to $ZADARMA_FROM)")
    cb.add_argument("--predicted", action="store_true", help="Predicted dial mode")
    cb.add_argument("--sip", help="Internal SIP to ring instead of PSTN number")

    rec = sub.add_parser("cdr", help="Call detail records")
    rec.add_argument("--start", required=True, help="YYYY-MM-DD")
    rec.add_argument("--end", required=True, help="YYYY-MM-DD")

    sms = sub.add_parser("sms", help="Send SMS")
    sms.add_argument("--to", required=True)
    sms.add_argument("--message", required=True)
    sms.add_argument("--caller-id", dest="caller_id")

    sc = sub.add_parser("save-creds", help="Persist credentials to ~/.hermes/.env")
    sc.add_argument("--key", required=True)
    sc.add_argument("--secret", required=True)
    sc.add_argument("--from", dest="default_from", help="Default caller number")

    args = p.parse_args(argv)

    if args.cmd == "save-creds":
        save_creds(args.key, args.secret, args.default_from)
        return 0
    if args.cmd == "balance":
        _print(balance()); return 0
    if args.cmd == "numbers":
        _print(numbers()); return 0
    if args.cmd == "callback":
        _print(callback(args.to, args.from_, args.predicted, args.sip)); return 0
    if args.cmd == "cdr":
        _print(cdr(args.start, args.end)); return 0
    if args.cmd == "sms":
        _print(send_sms(args.to, args.message, args.caller_id)); return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
