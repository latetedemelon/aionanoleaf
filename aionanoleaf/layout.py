"""Layout helpers: panel orientation and positions.

Exposes spec-aligned endpoints around /panelLayout.
- get_global_orientation(): int (0..360) if available
- set_global_orientation(angle): PUT {"value": angle}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LayoutClient:
    """Thin wrapper over a Nanoleaf-like client with _get_json/_put_json."""

    def __init__(self, nl: Any) -> None:
        self._nl = nl

    async def get_positions(self) -> List[Dict[str, int]]:
        """Return panelLayout.layout.positionData if present, else []."""
        # Prefer explicit endpoint if available
        data = None
        get_layout = getattr(self._nl, "_get_json", None)
        if callable(get_layout):
            try:
                data = await self._nl._get_json("/panelLayout/layout")  # type: ignore[attr-defined]
            except Exception:  # best-effort
                data = None

        if isinstance(data, dict):
            pos = data.get("positionData")
            if isinstance(pos, list):
                return [dict(p) for p in pos if isinstance(p, dict)]

        # Fallbacks: inspect cached .info/_info like DigitalTwin does
        info = getattr(self._nl, "info", None) or getattr(self._nl, "_info", None)
        if isinstance(info, dict):
            try:
                pos = info.get("panelLayout", {}).get("layout", {}).get("positionData")
                if isinstance(pos, list):
                    return [dict(p) for p in pos if isinstance(p, dict)]
            except Exception:
                return []
        return []

    async def get_global_orientation(self) -> Optional[int]:
        """GET /panelLayout/globalOrientation -> int or dict{'value': int}."""
        # pylint: disable=protected-access
        data = await self._nl._get_json("/panelLayout/globalOrientation")  # type: ignore[attr-defined]
        if isinstance(data, int):
            return data
        if isinstance(data, dict):
            val = data.get("value")
            if isinstance(val, int):
                return val
            try:
                return int(val)  # if stringified
            except Exception:
                return None
        return None

    async def set_global_orientation(self, angle: int) -> None:
        """PUT /panelLayout/globalOrientation with {'value': angle} (0..360)."""
        angle = int(angle)
        if angle < 0 or angle > 360:
            # be lenient: clamp, as most UIs do
            angle = max(0, min(360, angle))
        payload = {"value": angle}
        # pylint: disable=protected-access
        await self._nl._put_json("/panelLayout/globalOrientation", payload)  # type: ignore[attr-defined]
