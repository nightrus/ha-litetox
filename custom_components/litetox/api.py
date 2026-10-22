"""Small async client for the litetox proxy HTTP API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class LitetoxError(Exception):
    """Server unreachable or returned garbage."""


class LitetoxAuthError(LitetoxError):
    """Bad API token."""


class LitetoxNotFound(LitetoxError):
    """IMEI is not registered on the server."""


class LitetoxOffline(LitetoxError):
    """Tracker is not connected to the server right now."""


class LitetoxClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self._url = url.rstrip("/")
        self._token = token

    async def _req(self, method: str, path: str, body: dict | None = None) -> Any:
        try:
            async with asyncio.timeout(15):
                async with self._session.request(
                    method,
                    f"{self._url}{path}",
                    json=body,
                    headers={"Authorization": f"Bearer {self._token}"},
                ) as resp:
                    if resp.status == 401:
                        raise LitetoxAuthError("unauthorized")
                    if resp.status == 404:
                        raise LitetoxNotFound(path)
                    if resp.status == 409:
                        raise LitetoxOffline("device offline")
                    if resp.status >= 400:
                        raise LitetoxError(f"HTTP {resp.status}: {await resp.text()}")
                    return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise LitetoxError(str(err)) from err

    async def health(self) -> dict[str, Any]:
        return await self._req("GET", "/health")

    async def devices(self) -> list[dict[str, Any]]:
        return (await self._req("GET", "/devices"))["devices"]

    async def register(
        self, imei: str, name: str, upstream: str | None = None
    ) -> dict[str, Any]:
        """Register/enable the IMEI; upstream "host:port" (or "" = off) sets its ALTOX server."""
        body = {"imei": imei, "name": name}
        if upstream is not None:
            body["upstream"] = upstream
        return await self._req("POST", "/devices", body)

    async def unregister(self, imei: str) -> None:
        await self._req("DELETE", f"/devices/{imei}")

    async def state(self, imei: str) -> dict[str, Any]:
        return await self._req("GET", f"/state/{imei}")

    async def command(self, imei: str, command: str) -> int | None:
        """Queue a command; returns its id for status polling."""
        return (await self._req("POST", f"/cmd/{imei}", {"command": command})).get("id")

    async def command_status(self, imei: str, cmd_id: int) -> dict[str, Any]:
        return await self._req("GET", f"/cmd/{imei}/{cmd_id}")
