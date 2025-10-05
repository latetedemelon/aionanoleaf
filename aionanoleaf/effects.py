"""
Helpers for Nanoleaf Effects endpoints.

Covers:
- GET /effects/effectsList           -> list_effects()
- PUT /effects { "select": name }    -> select_effect()
- PUT /effects { "write": { ... } }  -> write_custom_effect()
- PUT /effects { "write": { "command": "displayTemp", ... } } -> display_temp_static()

These map to the public OpenAPI shapes as documented by Nanoleaf / community references.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


class EffectsClient:
    """High-level client bound to a Nanoleaf transport."""

    def __init__(self, nl: "Nanoleaf") -> None:
        # `Nanoleaf` is the main client providing _get_json/_put_json
        self._nl = nl

    async def list_effects(self) -> list[str]:
        """Return the list of available effect names."""
        data = await self._nl._get_json("/effects/effectsList")
        # API returns a JSON array of strings
        return list(data) if isinstance(data, Sequence) else []

    async def select_effect(self, name: str) -> None:
        """Select an existing effect by name."""
        await self._nl._put_json("/effects", {"select": name})

    async def write_custom_effect(
        self,
        anim_name: str,
        anim_data: str,
        *,
        color_type: str = "HSB",
        loop: bool = False,
        palette: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        """
        Upload (add/replace) a custom effect and select it.

        `anim_data` must be a valid Nanoleaf animData string. `palette` can be empty for static scenes.
        """
        payload: dict[str, Any] = {
            "write": {
                "command": "add",
                "animName": anim_name,
                "animType": "custom",
                "colorType": color_type,
                "loop": loop,
                "animData": anim_data,
                "palette": list(palette) if palette else [],
            }
        }
        await self._nl._put_json("/effects", payload)

    async def display_temp_static(
        self,
        anim_data: str,
        *,
        color_type: str = "HSB",
    ) -> None:
        """
        Temporarily display an effect without saving it (useful for Digital Twin previews).

        Uses the documented `displayTemp` command with `animType=custom`.
        """
        payload = {
            "write": {
                "command": "displayTemp",
                "animType": "custom",
                "colorType": color_type,
                "animData": anim_data,
            }
        }
        await self._nl._put_json("/effects", payload)
