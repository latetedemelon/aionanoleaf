"""Layout helpers: panel orientation and positions.

Exposes spec-aligned endpoints around /panelLayout.
- get_positions(): list of {panelId, x, y} dicts
- get_global_orientation(): int (0..360) if available
- set_global_orientation(angle): PUT {"value": angle}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Panel:
    """Runtime panel object with IDs and coordinates.

    Matches code paths that do `Panel(pid, x, y)` and may read `.panelId`
    (primary) or `.id` (alias property below).
    """
    panelId: int
    x: int
    y: int

    @property
    def id(self) -> int:  # compatibility with callers that expect `.id`
        return self.panelId


def _to_int(v: Any) -> Optional[int]:
    """Best-effort int conversion with Optional[Any] input."""
    if isinstance(v, bool):  # bool is int subclass; keep explicit
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return None
    return None


class LayoutClient:
    """Thin wrapper over a Nanoleaf-like client with _get_json/_put_json."""

    def __init__(self, nl: Any) -> None:
        self._nl = nl

    async def get_positions(self) -> List[Dict[str, int]]:
        """Return panelLayout.layout.positionData as normalized ints, else [].

        Output shape: [{"panelId": int, "x": int, "y": int}, ...]
        """
        data = None
        get_layout = getattr(self._nl, "_get_json", None)
        if callable(get_layout):
            try:
                # pylint: disable=protected-access
                data = await self._nl._get_json("/panelLayout/layout")  # type: ignore[attr-defined]
            except Exception:
                data = None

        pos = None
        if isinstance(data, dict):
            pos = data.get("positionData")

        # Fallbacks: inspect cached .info/_info
        if pos is None:
            info = getattr(self._nl, "info", None) or getattr(self._nl, "_info", None)
            if isinstance(info, dict):
                try:
                    pos = info.get("panelLayout", {}).get("layout", {}).get("positionData")
                except Exception:
                    pos = None

        out: List[Dict[str, int]] = []
        if isinstance(pos, list):
            for p in pos:
                if not isinstance(p, dict):
                    continue
                pid = _to_int(p.get("panelId"))
                x = _to_int(p.get("x"))
                y = _to_int(p.get("y"))
                if pid is not None and x is not None and y is not None:
                    out.append({"panelId": pid, "x": x, "y": y})
        return out

    async def get_global_orientation(self) -> Optional[int]:
        """GET /panelLayout/globalOrientation -> int or dict{'value': int}."""
        # pylint: disable=protected-access
        data = await self._nl._get_json("/panelLayout/globalOrientation")  # type: ignore[attr-defined]
        if isinstance(data, int):
            return data
        if isinstance(data, dict):
            raw = data.get("value")
            val = _to_int(raw)
            return val
        return None

    async def set_global_orientation(self, angle: int) -> None:
        """PUT /panelLayout/globalOrientation with {'value': angle} (0..360)."""
        a = int(angle)
        if a < 0 or a > 360:
            a = max(0, min(360, a))
        payload: Dict[str, int] = {"value": a}
        # pylint: disable=protected-access
        await self._nl._put_json("/panelLayout/globalOrientation", payload)  # type: ignore[attr-defined]
