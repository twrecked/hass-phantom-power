# ⚡ Phantom Power Editor

A visual web-based configuration editor for the [Phantom Power](https://github.com/twrecked/hass-phantom-power) Home Assistant custom component.

Hosted version available at: **[https://phantom-power-dot-twrecked-tools.nn.r.appspot.com](https://phantom-power-dot-twrecked-tools.nn.r.appspot.com)**

---

## Features

- **Device Discovery**: Browse your existing Home Assistant switches, lights, climate entities, and fans.
- **One-Click Electrify**: Add realistic power tracking and companion energy sensors with a single click.
- **Multi-State & Climate Rules**: Match operational stages and attributes (`equipment_running`, `aux_heat`, `fan`) to wattage levels with random jitter variance.
- **Power Groups**: Group individual power loads into aggregate energy monitoring categories.
- **Live Sync**: Save changes directly back into Home Assistant via an authenticated webhook callback.
- **Offline / Local Friendly**: Run locally on your network with zero external cloud dependencies.

---

## Running Locally (Private / Offline Mode)

If you prefer to run the editor locally on your home network without sending data through the cloud:

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python main.py
   ```
   By default, the editor runs at `http://localhost:8088`.

3. Connect to Home Assistant:
   - Go to **Settings -> Devices & Services -> Phantom Power -> Configure**.
   - Set **Editor URL** to your local address (e.g. `http://localhost:8088` or `http://192.168.1.X:8088`).
   - Click the link to open the local editor with your devices and existing configuration pre-loaded.

---

## Deployment to Google App Engine

The editor is configured as an App Engine service:

```bash
cd phantom-power-editor
gcloud app deploy app.yaml
```

*(Make sure an App Engine `default` service is deployed in your GCP project first).*
