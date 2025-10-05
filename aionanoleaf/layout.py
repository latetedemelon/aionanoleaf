# pylint: disable=invalid-name
"""Layout helpers: panel orientation and positions.

Exposes spec-aligned endpoints around /panelLayout.
- Panel(...) accepts either (panelId, x, y) or a single "position" object/dict.
- get_positions(): list of {panelId, x, y} dicts
- get_global_orientation(): int (0..360) if available
- set_global_orientation(angle): PUT {"value": angle}
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, overload


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


class Panel:
    """Runtime panel object with IDs and coordinates.

    Accepts either:
      - Panel(panelId: int, x: int, y: int)
      - Panel(pos: Mapping[str, Any])  # keys: panelId/x/y or id/x_coordinate/y_coordinate
      - Panel(pos: Any)  # object with attributes panelId/x/y or id/x_coordinate/y_coordinate

    Also exposes `.id` as an alias to `.panelId`.
    """

    panelId: int
    x: int
    y: int

    @overload
    def __init__(self, panelId: int, x: int, y: int) -> None: ...
    @overload
    def __init__(self, pos: Mapping[str, Any]) -> None: ...
    @overload
    def __init__(self, pos: Any) -> None: ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(args) == 1 and not kwargs:
            pos = args[0]
            # Mapping case
            if isinstance(pos, Mapping):
                pid = _to_int(pos.get("panelId"))
                if pid is None:
                    pid = _to_int(pos.get("id"))
                x = _to_int(pos.get("x"))
                if x is None:
                    x = _to_int(pos.get("x_coordinate"))
                y = _to_int(pos.get("y"))
                if y is None:
                    y = _to_int(pos.get("y_coordinate"))
            else:
                # Generic object with attributes
                pid_attr = getattr(pos, "panelId", None)
                if pid_attr is None:
                    pid_attr = getattr(pos, "id", None)
                x_attr = getattr(pos, "x", None)
                if x_attr is None:
                    x_attr = getattr(pos, "x_coordinate", None)
                y_attr = getattr(pos, "y", None)
                if y_attr is None:
                    y_attr = getattr(pos, "y_coordinate", None)
                pid = _to_int(pid_attr)
                x = _to_int(x_attr)
                y = _to_int(y_attr)

            if pid is None or x is None or y is None:
                raise TypeError("Panel(pos): could not extract panelId/x/y")
            self.panelId = pid
            self.x = x
            self.y = y
            return

        # Tuple/positional/keyword case
        if len(args) + len(kwargs) == 3:
            # Support both positional and keyword usage
            if args:
                try:
                    panel_id, x_val, y_val = args  # type: ignore[misc]
                except Exception as exc:
                    raise TypeError("Panel(panelId, x, y) requires three ints") from exc
            else:
                try:
                    panel_id = kwargs["panelId"]
                    x_val = kwargs["x"]
                    y_val = kwargs["y"]
                except KeyError as exc:
                    raise TypeError("Panel(panelId, x, y) missing keyword") from exc

            pid = _to_int(panel_id)
            x = _to_int(x_val)
            y = _to_int(y_val)
            if pid is None or x is None or y is None:
                raise TypeError("Panel(panelId, x, y) must be integers")
            self.panelId = pid
            self.x = x
            self.y = y
            return

        raise TypeError("Panel expects (panelId, x, y) or a single position object/dict")

    @property
    def id(self) -> int:  # compatibility with callers that expect `.id`
        return self.panelId


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
