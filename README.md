> [!WARNING]
> **Archived — use [latetedemelon/aionanoleaf2](https://github.com/latetedemelon/aionanoleaf2) instead.**
>
> This was a fork of [milanmeu/aionanoleaf](https://github.com/milanmeu/aionanoleaf),
> whose last release was in 2022. Home Assistant replaced that library with
> `aionanoleaf2` in core commit
> [8693294ea](https://github.com/home-assistant/core/commit/8693294ea), shipped
> in 2026.3, so this lineage is a dead end.
>
> Everything added here has moved to `aionanoleaf2`:
>
> | Here (0.5.0) | In aionanoleaf2 |
> | --- | --- |
> | `DigitalTwin` | `Nanoleaf.digital_twin()`, plus UDP streaming for animation |
> | `RhythmClient` | `get_rhythm()`, `set_rhythm_mode()` and the `rhythm_*` properties |
> | `LayoutClient` orientation | `get_global_orientation()` / `set_global_orientation()` |
> | `EffectsClient.get_rhythm_effects` | `get_rhythm_effects()`, `get_effect_details()` |
> | `DigitalTwin.apply_temp` | `DigitalTwin.show_temporarily()` |
>
> `aionanoleaf2` additionally supports Nanoleaf Essentials and Matter Wi-Fi
> devices, 4D screen-mirroring modes and IPv6 hosts, and fixes several bugs
> that were present here.
>
> [latetedemelon/ha-nanoleaf](https://github.com/latetedemelon/ha-nanoleaf)
> points at `aionanoleaf2` as of its 2.0.0 release.

# aioNanoleaf package 
[![PyPI](https://img.shields.io/pypi/v/aionanoleaf)](https://pypi.org/project/aionanoleaf/) ![PyPI - Downloads](https://img.shields.io/pypi/dm/aionanoleaf) [![PyPI - License](https://img.shields.io/pypi/l/aionanoleaf?color=blue)](https://github.com/milanmeu/aionanoleaf/blob/main/COPYING)

An async Python wrapper for the Nanoleaf API.

## Installation
```bash
pip install aionanoleaf
```

## Usage
### Import
```python
from aionanoleaf import Nanoleaf
```

### Create a `aiohttp.ClientSession` to make requests
```python
from aiohttp import ClientSession
session = ClientSession()
```

### Create a `Nanoleaf` instance
```python
from aionanoleaf import Nanoleaf
light = Nanoleaf(session, "192.168.0.100")
```

## Example
```python
from aiohttp import ClientSession
from asyncio import run

import aionanoleaf

async def main():
    async with ClientSession() as session:
        nanoleaf = aionanoleaf.Nanoleaf(session, "192.168.0.73")
        try:
            await nanoleaf.authorize()
        except aionanoleaf.Unauthorized as ex:
            print("Not authorizing new tokens:", ex)
            return
        await nanoleaf.turn_on()
        await nanoleaf.get_info()
        print("Brightness:", nanoleaf.brightness)
        await nanoleaf.deauthorize()
run(main())
```

## Digital Twin
```python
from aionanoleaf.digital_twin import DigitalTwin

twin = await DigitalTwin.create(light)   # factory resolves layout & IDs
await twin.set_color(panel_id, (255,0,0))
await twin.set_all_colors((0,0,0))
await twin.sync(transition_ms=100)       # builds & PUTs static scene
colors = twin.colors                     # dict view {id: (r,g,b)}
```

The `DigitalTwin`, `EffectsClient`, `LayoutClient` and `RhythmClient` helpers all
talk to the device through the same authenticated `Nanoleaf` transport, so you
can hand them a configured `Nanoleaf` instance directly.

## Effects
```python
from aionanoleaf import EffectsClient

effects = EffectsClient(light)
names = await effects.get_effects_list()      # GET /effects/effectsList
current = await effects.get_selected_effect() # GET /effects/select
await effects.select_effect(names[0])         # PUT /effects {"select": ...}
await effects.write_custom_effect("My FX", anim_data)  # add + select
```

## Layout / orientation
```python
from aionanoleaf import LayoutClient

layout = LayoutClient(light)
positions = await layout.get_positions()            # [{"panelId", "x", "y"}, ...]
angle = await layout.get_global_orientation()        # int degrees (0..360)
await layout.set_global_orientation(180)
```

## Rhythm / audio module (music sync)
```python
from aionanoleaf import EffectsClient, RhythmClient

rhythm = RhythmClient(light)
if await rhythm.is_connected():            # a sound module / mic is present
    aux = await rhythm.get_aux_available()  # 3.5mm aux input present?
    await rhythm.set_mode("microphone")     # or "aux" / 0 / 1
    print("listening:", await rhythm.is_active())

# Discover the sound-reactive ("music sync") effects, then select one:
effects = EffectsClient(light)
for name in await effects.get_rhythm_effects():  # pluginType == "rhythm"
    print("music effect:", name)
```
