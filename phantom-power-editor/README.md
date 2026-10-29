# ⚡ Phantom Power Editor

A visual web-based configuration editor for the [Phantom Power](https://github.com/twrecked/hass-phantom-power) Home Assistant custom component.

## Features

- **Device Discovery**: Browse your existing Home Assistant switches, lights, and fans.
- **One-Click Electrify**: Add realistic power tracking and companion energy sensors with a single click.
- **Power Groups**: Group individual power loads into aggregate energy monitoring categories.
- **Live Sync**: Save changes directly back into Home Assistant via an authenticated webhook callback.
- **Offline / Local Friendly**: Run locally on your network with zero external cloud dependencies.

## Running Locally

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python main.py
   ```
   By default, the editor runs at `http://localhost:8088`.

3. Open Home Assistant:
   - Go to **Settings -> Devices & Services -> Phantom Power -> Configure**.
   - Click the link to open the editor with your devices and existing configuration pre-loaded.
