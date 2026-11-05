"""GoMarble client: GA4, Meta, Search Console and (fallback) Google Ads.

GoMarble exposes its tools as an MCP server over streamable HTTP. With an API key from
https://apps.gomarble.ai/settings/api-keys a script can call it unattended:
POST JSON-RPC to https://apps.gomarble.ai/mcp-api/mcp with `Authorization: Bearer <key>`.

Every call can be recorded to, or replayed from, a cache directory. Replay is what lets the
builders be tested offline against a captured week.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

ENDPOINT = os.environ.get("GOMARBLE_MCP_URL", "https://apps.gomarble.ai/mcp-api/mcp")
PROTOCOL = "2025-03-26"


class GoMarbleError(RuntimeError):
    pass


class GoMarble:
    def __init__(self, api_key: str | None = None, cache_dir: str | Path | None = None,
                 replay_only: bool = False, timeout: int = 180):
        self.key = api_key or os.environ.get("GOMARBLE_API_KEY")
        self.cache = Path(cache_dir) if cache_dir else None
        self.replay_only = replay_only
        self.timeout = timeout
        self.session_id: str | None = None
        self._id = 0
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)
        if not self.key and not replay_only:
            raise GoMarbleError("GOMARBLE_API_KEY is not set.")

    # ------------------------------------------------------------------ transport
    def _post(self, body: dict) -> tuple[dict | None, requests.Response]:
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        r = requests.post(ENDPOINT, json=body, headers=headers, timeout=self.timeout)
        if r.status_code >= 400:
            raise GoMarbleError(f"GoMarble HTTP {r.status_code}: {r.text[:300]}")
        if "id" not in body:  # notification
            return None, r
        ctype = r.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            msg = None
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    if data.get("id") == body["id"]:
                        msg = data
            if msg is None:
                raise GoMarbleError("GoMarble stream ended without a response.")
            return msg, r
        return r.json(), r

    def _rpc(self, method: str, params: dict) -> dict:
        self._id += 1
        msg, _ = self._post({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        if "error" in msg:
            raise GoMarbleError(f"{method}: {msg['error']}")
        return msg["result"]

    def _ensure_session(self) -> None:
        if self.session_id is not None:
            return
        self._id += 1
        msg, r = self._post({
            "jsonrpc": "2.0", "id": self._id, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                       "clientInfo": {"name": "aqua-reports", "version": "1.0"}},
        })
        if "error" in msg:
            raise GoMarbleError(f"initialize: {msg['error']}")
        self.session_id = r.headers.get("Mcp-Session-Id", "")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # ------------------------------------------------------------------ tool calls
    @staticmethod
    def _key(tool: str, args: dict) -> str:
        raw = json.dumps([tool, args], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def call(self, tool: str, args: dict, retries: int = 1) -> dict:
        """Call a GoMarble tool and return its JSON result. A failed call is retried once."""
        path = self.cache / f"{tool}-{self._key(tool, args)}.json" if self.cache else None
        if path and path.exists():
            return json.loads(path.read_text())["result"]
        if self.replay_only:
            raise GoMarbleError(f"Not in replay cache: {tool} {json.dumps(args)[:200]}")
        last = None
        for attempt in range(retries + 1):
            try:
                self._ensure_session()
                res = self._rpc("tools/call", {"name": tool, "arguments": args})
                if res.get("isError"):
                    raise GoMarbleError(f"{tool}: {_text(res)[:400]}")
                out = json.loads(_text(res))
                if path:
                    path.write_text(json.dumps({"tool": tool, "args": args, "result": out}, ensure_ascii=False))
                return out
            except (GoMarbleError, requests.RequestException, json.JSONDecodeError) as e:
                last = e
                self.session_id = None
                time.sleep(3 * (attempt + 1))
        raise GoMarbleError(f"{tool} failed after {retries + 1} tries: {last}")


def _text(res: dict) -> str:
    for c in res.get("content", []):
        if c.get("type") == "text":
            return c["text"]
    if "structuredContent" in res:
        return json.dumps(res["structuredContent"])
    raise GoMarbleError("Tool result had no text content.")
