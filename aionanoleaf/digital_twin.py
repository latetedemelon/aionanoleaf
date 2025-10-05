# aionanoleaf/digital_twin.py
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple, Optional, Any
import asyncio

__all__ = ["DigitalTwin", "_build_anim"]

RGB = Tuple[int, int, int]


def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(v)))


def _validate_rgb(rgb: RGB) -> RGB:
    try:
        r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception as exc:  # pragma: no cover (defensive)
        raise ValueError("rgb must be a 3-tuple of integers") from exc
    for v in (r, g, b):
        if v < 0 or v > 255:
            raise ValueError("rgb components must be in [0,255]")
    return _clamp(r), _clamp(g), _clamp(b)


def _hex_to_rgb(s: str) -> RGB:
    if not isinstance(s, str) or not s:
        raise ValueError("hex string required")
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise ValueError("hex must be #RRGGBB")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b


def _apply_brightness(rgb: RGB, brightness: Optional[int]) -> RGB:
    if brightness is None:
        return rgb
    if not (0 <= int(brightness) <= 100):
        raise ValueError("brightness must be between 0 and 100")
    if brightness == 100:
        return rgb
    scale = brightness / 100.0
    r, g, b = rgb
    return (_clamp(round(r * scale)), _clamp(round(g * scale)), _clamp(round(b * scale)))


def _build_anim(
    ids: Iterable[int],
    colours: Dict[int, RGB],
    transition: int = 10,
    *,
    brightness: Optional[int] = None,
) -> str:
    """
    Build Nanoleaf 'static' effect animData string:
      <count> [panelId] 1 R G B 0 <transition_ms> ...
    """
    id_list = list(ids)
    records: List[int] = []
    t = int(max(0, transition))
    for pid in id_list:
        r, g, b = _apply_brightness(colours[pid], brightness)
        records += [int(pid), 1, int(r), int(g), int(b), 0, t]
    return " ".join(map(str, [len(id_list)] + records))


class _Panel:
    __slots__ = ("id", "x", "y")

    def __init__(self, id: int, x: int, y: int) -> None:
        self.id = int(id)
        self.x = int(x)
        self.y = int(y)


class DigitalTwin:
    """
    Per-panel static colour control over REST (no UDP).
    - Persistent or temporary application (display/displayTemp)
    - Subset updates (only=[...])
    - Optional brightness overlay 0..100
    - New: apply_temp() to blink and restore previous effect
    """

    def __init__(self, nl: Any, panels: List[_Panel]) -> None:
        self._nl = nl
        panels_sorted = sorted(panels, key=lambda p: (p.x, p.y, p.id))
        self._ids_ordered: Tuple[int, ...] = tuple(p.id for p in panels_sorted)
        self._ids_set = set(self._ids_ordered)
        self.colors: Dict[int, RGB] = {pid: (0, 0, 0) for pid in self._ids_ordered}

    @classmethod
    async def create(cls, nl: Any) -> "DigitalTwin":
        # Ensure device info/layout loaded if client requires it
        get_info = getattr(nl, "get_info", None)
        if callable(get_info):
            res = get_info()
            if asyncio.iscoroutine(res):
                await res

        layout = None
        if callable(getattr(nl, "get_panel_layout", None)):
            layout = await nl.get_panel_layout()
        elif callable(getattr(nl, "panel_layout", None)):
            layout = await nl.panel_layout()

        panels: List[_Panel] = []
        pos = None

        if isinstance(layout, dict):
            pos = layout.get("positionData")

        if pos is None:
            info = getattr(nl, "info", None) or getattr(nl, "_info", None)
            if isinstance(info, dict):
                try:
                    pos = (
                        info.get("panelLayout", {})
                        .get("layout", {})
                        .get("positionData", None)
                    )
                except Exception:
                    pos = None

        if isinstance(pos, list) and pos:
            for p in pos:
                pid = p.get("panelId")
                x = p.get("x")
                y = p.get("y")
                if pid is not None and x is not None and y is not None:
                    panels.append(_Panel(pid, x, y))

        if not panels:
            candidates = getattr(nl, "panels", None) or getattr(nl, "_panels", None)
            if isinstance(candidates, (list, tuple)) and candidates:
                for obj in candidates:
                    pid = getattr(obj, "id", None) or getattr(obj, "panelId", None)
                    x = getattr(obj, "x", None) or getattr(obj, "x_coordinate", None)
                    y = getattr(obj, "y", None) or getattr(obj, "y_coordinate", None)
                    if pid is not None and x is not None and y is not None:
                        panels.append(_Panel(pid, x, y))

        if not panels:
            raise RuntimeError(
                "Panel layout not found; per-panel control requires a panel device. "
                "If this is an Essentials bulb/strip, use whole-device colour/state APIs."
            )

        return cls(nl, panels)

    # -------- introspection --------

    @property
    def ids(self) -> List[int]:
        return list(self._ids_ordered)

    def get_color(self, panel_id: int) -> RGB:
        return self.colors[int(panel_id)]

    def get_all_colors(self) -> Dict[int, RGB]:
        return dict(self.colors)

    # -------- editing --------

    async def set_color(self, pid: int, rgb: RGB) -> None:
        pid = int(pid)
        if pid not in self._ids_set:
            raise ValueError(f"panel id unknown: {pid}")
        self.colors[pid] = _validate_rgb(rgb)

    async def set_hex(self, pid: int, hex_colour: str) -> None:
        await self.set_color(pid, _hex_to_rgb(hex_colour))

    async def set_all_colors(self, rgb: RGB) -> None:
        rgb = _validate_rgb(rgb)
        for pid in self._ids_ordered:
            self.colors[pid] = rgb

    # -------- rendering --------

    async def sync(
        self,
        *,
        transition_ms: int = 10,
        command: str = "display",
        only: Optional[Iterable[int]] = None,
        brightness: Optional[int] = None,
    ) -> None:
        """
        Apply current colours as a static scene.

        Args:
          transition_ms: per-panel transition (ms)
          command: "display" (persistent) or "displayTemp" (ephemeral)
          only: subset of panel IDs
          brightness: optional 0..100 scale applied to RGB
        """
        if command not in ("display", "displayTemp"):
            raise ValueError('command must be "display" or "displayTemp"')

        if only is None:
            ids: Iterable[int] = self._ids_ordered
        else:
            only_set = set(int(x) for x in only)
            unknown = only_set - self._ids_set
            if unknown:
                raise ValueError(f"unknown panel ids: {sorted(unknown)}")
            ids = tuple(pid for pid in self._ids_ordered if pid in only_set)

        anim = _build_anim(ids, self.colors, transition_ms, brightness=brightness)
        payload = {
            "command": command,
            "version": "1.0",
            "animType": "static",
            "animData": anim,
            "palette": [],
            "loop": False,
        }

        write_effect = getattr(self._nl, "write_effect", None)
        if callable(write_effect):
            res = write_effect(payload)
            if asyncio.iscoroutine(res):
                await res
            return

        for name in ("effects_write", "display_effect"):
            meth = getattr(self._nl, name, None)
            if callable(meth):
                res = meth(payload)
                if asyncio.iscoroutine(res):
                    await res
                return

        raise RuntimeError(
            "Nanoleaf client does not expose a write_effect/effects_write/display_effect method."
        )

    async def apply_temp(
        self,
        *,
        transition_ms: int = 60,
        duration_ms: int = 2000,
        only: Optional[Iterable[int]] = None,
        brightness: Optional[int] = None,
    ) -> None:
        """
        Blink: temporarily apply the current twin colours, then restore prior effect.

        Steps:
          1) Remember the currently selected effect
          2) displayTemp the static scene built from twin colours
          3) sleep 'duration_ms'
          4) re-select the previous effect (best effort)
        """
        # Lazy import to avoid hard dependency at import-time
        from aionanoleaf.effects import EffectsClient, UnauthorizedError  # type: ignore

        ef = EffectsClient(self._nl)
        prev = None
        try:
            prev = await ef.get_selected_effect()
        except Exception:
            # If we can't read it, still try to apply temp; restoration may be skipped.
            prev = None

        try:
            await self.sync(
                transition_ms=transition_ms,
                command="displayTemp",
                only=only,
                brightness=brightness,
            )
            await asyncio.sleep(max(0, int(duration_ms)) / 1000.0)
        finally:
            if prev:
                try:
                    await ef.select_effect(prev)
                except UnauthorizedError:
                    # pairing lost; nothing else to do
                    pass
                except Exception:
                    # best effort; swallow to avoid crashing caller
                    pass
