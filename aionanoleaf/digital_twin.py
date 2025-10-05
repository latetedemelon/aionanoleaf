"""Digital Twin helpers for per-panel static colour control over REST.

Features:
- Persistent or temporary application (display/displayTemp)
- Subset updates (only=[...])
- Optional brightness overlay (0..100)
- apply_temp(): blink a set of panels then restore previous effect
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple, Optional

from aionanoleaf.effects import EffectsClient  # top-level import (no C0415)

RGB = Tuple[int, int, int]
__all__ = ["DigitalTwin", "_build_anim"]


def _clamp(value: int, lo: int = 0, hi: int = 255) -> int:
    """Clamp integer to [lo, hi]."""
    return max(lo, min(hi, int(value)))


def _validate_rgb(rgb: RGB) -> RGB:
    """Validate and clamp an (R,G,B) 0..255 tuple."""
    try:
        r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    except Exception as exc:  # noqa: BLE001 (defensive parse)
        raise ValueError("rgb must be a 3-tuple of integers") from exc
    for v in (r, g, b):
        if v < 0 or v > 255:
            raise ValueError("rgb components must be in [0,255]")
    return _clamp(r), _clamp(g), _clamp(b)


def _hex_to_rgb(s: str) -> RGB:
    """Convert #RRGGBB string to an (R,G,B) tuple."""
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
    """Apply optional brightness overlay (0..100) to RGB."""
    if brightness is None:
        return rgb
    if not 0 <= int(brightness) <= 100:  # no superfluous parens
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
    """Build Nanoleaf 'static' effect animData string: N [id] 1 R G B 0 T ..."""
    id_list = list(ids)
    records: List[int] = []
    t = int(max(0, transition))
    for panel_id in id_list:
        r, g, b = _apply_brightness(colours[panel_id], brightness)
        records += [int(panel_id), 1, int(r), int(g), int(b), 0, t]
    return " ".join(map(str, [len(id_list)] + records))


@dataclass  # data container; keep tiny
class _Panel:  # pylint: disable=too-few-public-methods
    """Minimal panel record."""
    panel_id: int
    x: int
    y: int


class DigitalTwin:
    """Per-panel static colour control via REST Effects write."""

    def __init__(self, nl: Any, panels: List[_Panel]) -> None:
        """Create a twin given a Nanoleaf client and panel list."""
        self._nl = nl
        # Deterministic order: x asc, then y asc, then id asc
        panels_sorted = sorted(panels, key=lambda p: (p.x, p.y, p.panel_id))
        self._ids_ordered: Tuple[int, ...] = tuple(p.panel_id for p in panels_sorted)
        self._ids_set = set(self._ids_ordered)
        self.colors: Dict[int, RGB] = {pid: (0, 0, 0) for pid in self._ids_ordered}

    @classmethod
    async def create(cls, nl: Any) -> "DigitalTwin":
        """Fetch layout/positions from the device and return a twin."""
        # Some clients lazily populate info/layout
        get_info = getattr(nl, "get_info", None)
        if callable(get_info):
            result = get_info()
            if hasattr(result, "__await__"):
                await result

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
                # Be liberal with missing keys across firmwares
                try:
                    pos = (
                        info.get("panelLayout", {})
                        .get("layout", {})
                        .get("positionData", None)
                    )
                except (AttributeError, KeyError, TypeError):
                    pos = None

        if isinstance(pos, list) and pos:
            for p in pos:
                pid = p.get("panelId")
                x = p.get("x")
                y = p.get("y")
                if pid is not None and x is not None and y is not None:
                    panels.append(_Panel(int(pid), int(x), int(y)))

        if not panels:
            candidates = getattr(nl, "panels", None) or getattr(nl, "_panels", None)
            if isinstance(candidates, (list, tuple)) and candidates:
                for obj in candidates:
                    pid = getattr(obj, "panelId", None) or getattr(obj, "id", None)
                    x = getattr(obj, "x", None) or getattr(obj, "x_coordinate", None)
                    y = getattr(obj, "y", None) or getattr(obj, "y_coordinate", None)
                    if pid is not None and x is not None and y is not None:
                        panels.append(_Panel(int(pid), int(x), int(y)))

        if not panels:
            raise RuntimeError(
                "Panel layout not found; per-panel control requires a panel device. "
                "If this is an Essentials bulb/strip, use whole-device colour/state APIs."
            )

        return cls(nl, panels)

    # ---------- Introspection ----------

    @property
    def ids(self) -> List[int]:
        """List of panel IDs in deterministic (x,y,id) order."""
        return list(self._ids_ordered)

    def get_color(self, panel_id: int) -> RGB:
        """Get the current RGB assigned to a panel in the twin."""
        return self.colors[int(panel_id)]

    def get_all_colors(self) -> Dict[int, RGB]:
        """Get a copy of the whole twin colour map."""
        return dict(self.colors)

    # ---------- Editing ----------

    async def set_color(self, panel_id: int, rgb: RGB) -> None:
        """Set RGB for a single panel ID."""
        panel_id = int(panel_id)
        if panel_id not in self._ids_set:
            raise ValueError(f"panel id unknown: {panel_id}")
        self.colors[panel_id] = _validate_rgb(rgb)

    async def set_hex(self, panel_id: int, hex_colour: str) -> None:
        """Set RGB for a single panel using a #RRGGBB string."""
        await self.set_color(panel_id, _hex_to_rgb(hex_colour))

    async def set_all_colors(self, rgb: RGB) -> None:
        """Set RGB for all panels."""
        rgb = _validate_rgb(rgb)
        for panel_id in self._ids_ordered:
            self.colors[panel_id] = rgb

    # ---------- Rendering ----------

    async def sync(
        self,
        *,
        transition_ms: int = 10,
        command: str = "display",
        only: Optional[Iterable[int]] = None,
        brightness: Optional[int] = None,
    ) -> None:
        """Apply current colours as a static scene via /effects write."""
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
            result = write_effect(payload)
            if hasattr(result, "__await__"):
                await result
            return

        for name in ("effects_write", "display_effect"):
            meth = getattr(self._nl, name, None)
            if callable(meth):
                result = meth(payload)
                if hasattr(result, "__await__"):
                    await result
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
        """Blink: temporarily apply the twin colours, then restore previous effect."""
        ef = EffectsClient(self._nl)

        prev = None
        try:
            prev = await ef.get_selected_effect()
        except Exception:  # best-effort restore if readable
            prev = None

        try:
            await self.sync(
                transition_ms=transition_ms,
                command="displayTemp",
                only=only,
                brightness=brightness,
            )
            # Sleep non-negative duration
            await self._sleep_ms(max(0, int(duration_ms)))
        finally:
            if prev:
                try:
                    await ef.select_effect(prev)
                except Exception:
                    # Restoration is best-effort; ignore on failure.
                    pass

    @staticmethod
    async def _sleep_ms(ms: int) -> None:
        """Await sleep for ms milliseconds (tiny wrapper for testing)."""
        import asyncio  # local import keeps module imports minimal
        await asyncio.sleep(ms / 1000.0)
