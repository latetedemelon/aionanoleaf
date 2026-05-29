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

## Rhythm / audio module
```python
from aionanoleaf import RhythmClient

rhythm = RhythmClient(light)
if await rhythm.is_active():
    await rhythm.set_mode("aux")  # or "microphone" / 0 / 1
```
