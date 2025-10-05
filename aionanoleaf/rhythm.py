"""Rhythm helpers.

GET /rhythm returns a dict containing fields like:
- rhythmId, hardwareVersion, firmwareVersion
- rhythmActive (bool), rhythmMode (int), rhythmPos (panelId)
Some devices support setting rhythmMode via PUT /rhythm { "rhythmMode": <int> }.

This client exposes a safe superset: it reads the dict as-is and provides
helpers for common keys. set_mode() accepts int or 'microphone'/'aux'.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


_MODE_MAP = {
    "microphone": 0,
    "mic": 0,
    "aux": 1,
}


class RhythmClient:
    """Thin wrapper over a Nanoleaf-like client with _get_json/_put_json."""

    def __init__(self, nl: Any) -> None:
        self._nl = nl

    async def get_info(self) -> Dict[str, object]:
        """Return raw /rhythm dict; {} on failure."""
        # pylint: disable=protected-access
        try:
            data = await self._nl._get_json("/rhythm")  # type: ignore[attr-defined]
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    async def is_active(self) -> bool:
        """Return /rhythm.rhythmActive if present."""
        info = await self.get_info()
        val = info.get("rhythmActive")
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes", "on")
        return False

    async def get_mode(self) -> Optional[int]:
        """Return /rhythm.rhythmMode as int if present."""
        info = await self.get_info()
        val = info.get("rhythmMode")
        try:
            return int(val)  # type: ignore[arg-type]
        except Exception:
            return None

    async def set_mode(self, mode: int | str) -> None:
        """PUT /rhythm with {'rhythmMode': <int>}.

        Accepts: 0/1 or 'microphone'/'mic'/'aux'.
        """
        if isinstance(mode, str):
            m = _MODE_MAP.get(mode.strip().lower())
            if m is None:
                raise ValueError("mode must be 0/1 or 'microphone'/'mic'/'aux'")
            mode_int = m
        else:
            mode_int = int(mode)
            if mode_int not in (0, 1):
                raise ValueError("mode must be 0 or 1")
        payload = {"rhythmMode": mode_int}
        # pylint: disable=protected-access
        await self._nl._put_json("/rhythm", payload)  # type: ignore[attr-defined]
