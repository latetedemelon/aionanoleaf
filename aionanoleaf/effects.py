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

    async def get_effects_detail(self) -> list[dict]:
        """Return full metadata for every stored effect.

        Issues ``PUT /effects`` with the ``requestAll`` command and returns the
        ``animations`` list. Each item includes ``animName`` and, for plugin
        effects, ``pluginType``. Returns ``[]`` if the device/firmware does not
        answer in the expected shape.
        """
        # pylint: disable=protected-access
        data = await self._nl._put_json(  # type: ignore[attr-defined]
            "/effects", {"write": {"command": "requestAll"}}
        )
        if isinstance(data, dict):
            anims = data.get("animations")
            if isinstance(anims, list):
                return [a for a in anims if isinstance(a, dict)]
        return []

    async def get_rhythm_effects(self) -> list[str]:
        """Return the names of sound-reactive (rhythm) effects.

        A rhythm effect is a plugin effect whose ``pluginType`` is ``"rhythm"``;
        these react to audio captured by the device's microphone (or aux input),
        i.e. they are the "music sync" effects.
        """
        names: list[str] = []
        for anim in await self.get_effects_detail():
            if anim.get("pluginType") == "rhythm":
                name = anim.get("animName")
                if isinstance(name, str):
                    names.append(name)
        return names

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
    async def write_custom_effect(  # pylint: disable=too-many-arguments
        self,
        anim_name: str,
        anim_data: str,
        *,
        color_type: str = "HSB",
        loop: bool = False,
        palette: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
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
