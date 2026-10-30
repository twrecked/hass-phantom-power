# ⚡ Phantom Power for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Version](https://img.shields.io/badge/version-v0.1.0--alpha.1-blue.svg)](docs/RELEASE_NOTES_v0.1.0-alpha.1.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Phantom Power** is a Home Assistant custom component that generates synthetic power (Watts) and cumulative energy (kWh) tracking for devices that do not report their own power usage (dumb switches, dimmers, fans, appliances, and smart plugs).

Instead of setting up cumbersome template sensors and manually juggling Riemann sum helpers in the Home Assistant UI, Phantom Power lets you define synthetic power sensors, aggregate groups, and self-accumulating energy sensors directly in a clean YAML configuration.

---

## ✨ Features

- **💡 Realistic Power Sensors (`power_sensors`)**:
  - **Dimmer Scaling**: Scales power consumption linearly based on brightness (0–255) for lights or speed percentage (0–100%) for fans.
  - **Idle / Standby Draw**: Configures resting wattage (`standby_power`) when an appliance or switch is turned off.
  - **Device Registry Linking**: Automatically attaches synthetic power sensors to the original device in Home Assistant's Device Registry.
- **📈 Built-in Energy Accumulation (`energy_sensors`)**:
  - Direct integration from Watts into accumulating `kWh` without creating helper entities in the UI.
  - Dual integration engine: updates on power state changes and runs a periodic 30-second background tick so steady loads continue accumulating smoothly.
  - Persistent state restoration across Home Assistant restarts and host reboots.
  - Fully compatible with Home Assistant's native **Energy Dashboard** (`state_class: total_increasing`, `device_class: energy`).
- **🗂️ Power Groups (`group_sensors`)**:
  - Combines multiple power sensors into a unified load reading in Watts.
  - Can feed directly into a Phantom Energy sensor to monitor categories (e.g., *All Lights*, *Entertainment Center*, *Kitchen Appliances*).
  - Diagnostic attributes show individual member wattage breakdown and active device counts.
- **🎛️ Multi-State & Climate Rules (`states`)**:
  - Match operational stages or attributes (e.g., `equipment_running`, `aux_heat`, `fan`, `preset_mode`) to wattage levels.
  - Realistic jitter/noise simulation (`variance`) to model authentic electrical fluctuations.
- **🔄 Hot Configuration Reload**:
  - Reload YAML configuration on-the-fly with the `phantom_power.reload` service—no Home Assistant restart required.

---

## 🌐 Visual Web Editor

Phantom Power includes an interactive visual web editor to inspect your existing Home Assistant devices, configure power tracking with one click, build multi-state rules, and manage aggregate groups:

- **Hosted Cloud Builder:** Live on Google App Engine at **[https://phantom-power-dot-twrecked-tools.nn.r.appspot.com](https://phantom-power-dot-twrecked-tools.nn.r.appspot.com)**.
- **One-Click Sync via Home Assistant:** In Home Assistant, go to **Settings -> Devices & Services -> Phantom Power -> Configure**. Click **Open Phantom Power Editor** to launch the editor with your existing candidate devices and current configuration pre-loaded. Click **Save & Sync to Home Assistant**, and the editor automatically updates your file on disk and reloads the integration via an authenticated webhook.
- **Local & Offline Mode:** Prefer zero data leaving your local network? Run the editor locally with `python main.py` in the `phantom-power-editor/` folder, and set the **Editor URL** in Home Assistant to `http://localhost:8088` (or your LAN IP).
- **Manual Export & Import:** Full support for copying YAML to your clipboard, downloading the file, or pasting existing YAML directly into the editor.

---

## 📦 Installation

### HACS (Recommended)
1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add the repository URL, select **Integration** as the category, and click **Add**.
4. Search for **Phantom Power**, click **Download**, and restart Home Assistant.

### Manual Installation via `install` Script
From the repository directory, run:
```bash
./install /path/to/homeassistant/config
```
To perform the copy operation, add `go`:
```bash
./install go /path/to/homeassistant/config
```

---

## ⚙️ Configuration

Phantom Power can be configured via `/config/phantom_power.yaml` or directly inside `/config/configuration.yaml`.

### Example `/config/phantom_power.yaml`:

```yaml
phantom_power:
  # ------------------------------------------------------------------
  # Power Sensors: Associate wattage with any existing entity
  # ------------------------------------------------------------------
  power_sensors:
    # Dimmable light: adjusts wattage between 1.0W and 12.0W based on brightness
    - name: "Dining Room Lights Power"
      entity_id: light.dining_room
      power: 12.0             # Rated Watts at 100% brightness
      min_power: 1.0          # Minimum Watts when dimmed to 1%
      standby_power: 0.0      # Watts when turned off
      link_device: true       # Attach to the dining room light device in HA

    # Smart switch with standby power draw
    - name: "Coffee Maker Power"
      entity_id: switch.coffee_maker
      power: 1250.0           # Active brewing wattage
      standby_power: 1.8      # Standby clock draw when off
      link_device: true

    # Ceiling fan: scales wattage with fan percentage
    - name: "Living Room Fan Power"
      entity_id: fan.living_room_fan
      power: 65.0
      min_power: 12.0
      standby_power: 0.5
      link_device: true

  # ------------------------------------------------------------------
  # Group Sensors: Aggregate multiple power sensors into a total load
  # ------------------------------------------------------------------
  group_sensors:
    - name: "All Lights Power Group"
      entities:
        - sensor.dining_room_lights_power
        - sensor.kitchen_lights_power

  # ------------------------------------------------------------------
  # Energy Sensors: Self-accumulating kWh for the Energy Dashboard
  # ------------------------------------------------------------------
  energy_sensors:
    # Individual device energy monitor
    - name: "Dining Room Lights Energy"
      power_sensor: sensor.dining_room_lights_power
      integration_method: trapezoidal

    # Whole-group energy monitor
    - name: "All Lights Energy Group"
      power_sensor: sensor.all_lights_power_group
      integration_method: trapezoidal
```

---

## 📖 Configuration Reference

### `power_sensors`

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | **Required** | Friendly name of the sensor. Determines the entity ID (`sensor.<name>`). |
| `entity_id` | string | **Required** | The target Home Assistant entity to track (e.g. `light.dining_room`, `switch.plug`). |
| `power` | float | **Required** | The rated power draw in Watts when active / 100% on. |
| `min_power` | float | `0.0` | Minimum power draw in Watts when dimmed or set to lowest speed. |
| `standby_power` | float | `0.0` | Power draw in Watts when the entity is `off` or idling. |
| `link_device` | boolean | `true` | When `true`, links this power sensor to the target entity's device in the Device Registry. |
| `unique_id` | string | *auto* | Optional unique ID for entity registry customization. |

### Multi-Stage & Climate Rule Mapping (`states`)

For devices like thermostats, heat pumps, vacuums, or multi-speed appliances where wattage depends on operational stages or attributes:

```yaml
phantom_power:
  power_sensors:
    - name: "Main Thermostat Power"
      entity_id: climate.main_thermostat
      standby_power: 0.0          # Wattage when idling or off
      variance: 25.0              # Optional ±25W random jitter to look authentic
      link_device: true
      states:
        # Evaluated top-to-bottom (case-insensitive substring or value check)
        - attribute: aux_heat
          value: "on"
          power: 11000.0

        - attribute: equipment_running
          contains: "auxHeat1"
          power: 16000.0

        - attribute: equipment_running
          contains: "heatPump2"
          power: 3000.0

        - attribute: equipment_running
          contains: "compCool2"
          power: 2500.0

        - attribute: equipment_running
          contains: "compCool1"
          power: 2000.0

        - attribute: equipment_running
          contains: "heatPump"
          power: 2000.0

        - attribute: fan
          value: "on"
          power: 50.0
```

| Rule Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `attribute` | string | *optional* | Attribute name to inspect. If omitted, matches the primary entity `state`. |
| `contains` | string | *optional* | Case-insensitive substring match or list membership check. |
| `value` | string | *optional* | Case-insensitive exact match. |
| `power` | float | **Required** | Power draw in Watts when this rule matches. |

### `group_sensors`

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | **Required** | Friendly name of the group sensor (`sensor.<name>`). |
| `entities` | list | **Required** | List of power entity IDs to sum together. |
| `unique_id` | string | *auto* | Optional unique ID. |

### `energy_sensors`

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string | **Required** | Friendly name of the energy sensor (`sensor.<name>`). |
| `power_sensor` | string | **Required** | Entity ID of the power sensor to integrate (Watts or kW). |
| `integration_method` | string | `trapezoidal` | Integration algorithm: `trapezoidal` or `left`. |
| `initial_value` | float | `0.0` | Initial starting value in kWh. |
| `unique_id` | string | *auto* | Optional unique ID. |

---

## 🛠️ Services

### `phantom_power.reload`
Reloads the configuration file without restarting Home Assistant.
```yaml
service: phantom_power.reload
```

### `phantom_power.reset_energy`
Resets the accumulated energy of one or more Phantom Energy sensors to 0 (or a specified starting value).
```yaml
service: phantom_power.reset_energy
target:
  entity_id: sensor.dining_room_lights_energy
data:
  value: 0.0
```

---

## 📊 Energy Dashboard Setup

To track phantom devices on the Home Assistant Energy tab:
1. Navigate to **Settings -> Dashboards -> Energy**.
2. Under **Individual Devices**, click **Add Device**.
3. Select any Phantom Energy sensor (e.g., `sensor.dining_room_lights_energy` or `sensor.all_lights_energy_group`).
4. Home Assistant will immediately start recording consumption into long-term statistics.

---

## 📄 License

This project is licensed under the MIT License.
