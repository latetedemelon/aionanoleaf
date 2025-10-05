# aionanoleaf/effects.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, Optional


class APIError(RuntimeError):
    """Generic API error for Nanoleaf /effects calls."""


class UnauthorizedError(APIError):
    """401/403; pairing/token invalid or revoked."""


class UnavailableError(APIError):
    """Network errors or device offline."""


def _bracket_ipv6(host: str) -> str:
    """Wrap IPv6 literals in [] so URLs are valid."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


class EffectsClient:
    """
    Spec-aligned helpers for the Nanoleaf Effects API.

    This class avoids editing the core Nanoleaf client. It discovers a working
    session + base URL from a provided Nanoleaf-like object and performs:
      - GET /effects/effectsList
      - GET /effects/select
      - PUT /effects  (with {"select": ...} or {"write": {...}})
    """

    def __init__(self, nl: Any):
        self._nl = nl
        self._session = getattr(nl, "session", None) or getattr(nl, "_session", None)
        if self._session is None:
            raise APIError(
                "Nanoleaf client has no aiohttp session (.session or ._session)."
            )
        base = getattr(nl, "base_url", None) or getattr(nl, "url", None)
        if not base:
            host = getattr(nl, "host", None) or getattr(nl, "ip", None)
            token = getattr(nl, "token", None) or getattr(nl, "auth_token", None)
            if not host or not token:
                raise APIError(
                    "Cannot derive base URL; need .base_url/.url or (host/ip + token)."
                )
            base = f"http://{_bracket_ipv6(str(host))}:16021/api/v1/{token}"
        self._base = str(base).rstrip("/")

    # -------------------- public API --------------------

    async def get_effects_list(self) -> List[str]:
        data = await self._get_json("/effects/effectsList")
        # spec: returns array of names
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return data
        raise APIError(f"Unexpected effectsList payload: {data!r}")

    async def get_selected_effect(self) -> str:
        data = await self._get_json("/effects/select")
        # spec: returns string effect name
        if isinstance(data, str):
            return data
        # some firmwares return {"select": "<name>"} — be liberal
        if isinstance(data, dict) and isinstance(data.get("select"), str):
            return data["select"]
        raise APIError(f"Unexpected select payload: {data!r}")

    async def select_effect(self, name: str) -> None:
        await self._put_json("/effects", {"select": str(name)})

    async def write_effect(self, write_dict: Mapping[str, object]) -> None:
        await self._put_json("/effects", {"write": dict(write_dict)})

    # -------------------- internals --------------------

    async def _get_json(self, path: str) -> Any:
        try:
            async with self._session.get(self._base + path) as resp:
                txt = await resp.text()
                if resp.status == 401 or resp.status == 403:
                    raise UnauthorizedError(f"{resp.status}: {txt}")
                if resp.status >= 400:
                    raise APIError(f"GET {path} -> {resp.status}: {txt}")
                return await resp.json()
        except UnauthorizedError:
            raise
        except Exception as e:  # network, decode, etc.
            raise UnavailableError(str(e)) from e

    async def _put_json(self, path: str, body: Mapping[str, object]) -> None:
        try:
            async with self._session.put(self._base + path, json=body) as resp:
                txt = await resp.text()
                if resp.status == 401 or resp.status == 403:
                    raise UnauthorizedError(f"{resp.status}: {txt}")
                if resp.status >= 400:
                    # include a snippet of the body for debugging bad writes
                    raise APIError(
                        f"PUT {path} -> {resp.status}: {txt} | body_keys={list(body.keys())}"
                    )
        except UnauthorizedError:
            raise
        except Exception as e:
            raise UnavailableError(str(e)) from e
