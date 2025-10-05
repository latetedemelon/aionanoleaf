"""Helpers for Nanoleaf Effects endpoints.

This module does not assume a specific transport; it calls into the provided
Nanoleaf client for HTTP via ``_get_json`` and ``_put_json`` methods.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class EffectsClient:
    """Spec-aligned helpers for Effects list/select/write."""

    def __init__(self, nl: Any) -> None:
        """Bind to a Nanoleaf-like client that exposes _get_json/_put_json."""
        self._nl = nl

    async def get_effects_list(self) -> list[str]:
        """Return the list of available effect names."""
        # pylint: disable=protected-access
        data = await self._nl._get_json("/effects/effectsList")  # type: ignore[attr-defined]
        return [str(x) for x in data] if isinstance(data, Sequence) else []

    async def get_selected_effect(self) -> str:
        """Return the currently selected effect name."""
        # pylint: disable=protected-access
        data = await self._nl._get_json("/effects/select")  # type: ignore[attr-defined]
        if isinstance(data, str):
            return data
        if isinstance(data, dict) and isinstance(data.get("select"), str):
            return str(data["select"])
        return ""

    async def select_effect(self, name: str) -> None:
        """Select an existing effect by name."""
        # pylint: disable=protected-access
        await self._nl._put_json("/effects", {"select": str(name)})  # type: ignore[attr-defined]

    async def write_effect(self, write_dict: Mapping[str, object]) -> None:
        """PUT /effects with a {'write': {...}} payload (no validation)."""
        # pylint: disable=protected-access
        body = {"write": dict(write_dict)}
        await self._nl._put_json("/effects", body)  # type: ignore[attr-defined]

    # Convenience aliases (optional)
    async def write_custom_effect(
        self,
        anim_name: str,
        anim_data: str,
        *,
        color_type: str = "HSB",
        loop: bool = False,
        palette: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:  # pylint: disable=too-many-arguments
        """Add/replace a custom effect and select it immediately."""
        payload: dict[str, Any] = {
            "command": "add",
            "animName": anim_name,
            "animType": "custom",
            "colorType": color_type,
            "loop": loop,
            "animData": anim_data,
            "palette": list(palette) if palette else [],
        }
        await self.write_effect(payload)

    async def display_temp_static(self, anim_data: str, *, color_type: str = "HSB") -> None:
        """Temporarily display a custom/static effect without saving it."""
        payload = {
            "command": "displayTemp",
            "animType": "custom",
            "colorType": color_type,
            "animData": anim_data,
        }
        await self.write_effect(payload)
