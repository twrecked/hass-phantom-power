# 🚀 Phantom Power v0.1.0-alpha.1 — Synthetic Power & Energy Simulation for Home Assistant

> ### ⚠️ Alpha Release Notice
> **Phantom Power v0.1.0-alpha.1 is the initial alpha release of a dedicated Home Assistant integration for synthesizing power (Watts) and energy (kWh) metrics for non-reporting devices, dimmers, climate equipment, appliances, and aggregated groups.**
>
> Community testing and feedback are essential! If you encounter any bugs, state restoration regressions, or configuration issues, please open an issue with your configuration snippet and debug logs.

---

## 🌟 Highlights

### 1. Interactive Web-Based Visual Editor
Configure your phantom power devices visually or sync directly from Home Assistant:
- **Hosted Cloud Builder:** Live on Google App Engine at **[https://phantom-power-dot-twrecked-tools.nn.r.appspot.com](https://phantom-power-dot-twrecked-tools.nn.r.appspot.com)**.
- **One-Click Sync via Home Assistant:** In Home Assistant, click **Configure** on Phantom Power to launch the editor with your existing devices and configuration pre-loaded. Click **Save & Sync to Home Assistant**, and the editor automatically updates your file on disk and reloads the integration via an authenticated webhook.
- **Automatic Device Discovery:** Automatically discovers your switches, lights, climate units, and fans with one-click "Add Power & Energy" actions.
- **Local & Offline Mode:** Run the editor locally with `python main.py` in the `phantom-power-editor/` folder with zero data leaving your local network.

---

### 2. Virtual Power Sensors with Linear Dimmer Scaling
Associate realistic wattage measurements with any existing Home Assistant entity:
- **Dimmable Lights:** Automatically computes real-time wattage based on light `brightness` (0–255), scaling linearly between `min_power` and `power`.
- **Fans & Speed Controllers:** Scales wattage linearly with the `percentage` attribute (0–100%).
- **On/Off Appliances & Outlets:** Reports rated wattage when active and `standby_power` (e.g. 0.5–2W) when switched off or idling.
- **Configurable Device Linking:** Set `link_device: true` to automatically link the synthetic power sensor directly to the source entity's existing device in Home Assistant's Device Registry, making it show up directly on the device card.

---

### 3. Multi-Stage & Climate Rule Mapping (`states`)
Easily model complex, multi-stage devices like heat pumps, thermostats (e.g. ecobee), vacuums, and multi-speed appliances:
- **Sequential Evaluation:** Rules are evaluated top-to-bottom; the first matching rule sets the current wattage.
- **Case-Insensitive Operators:** Supports exact equality (`value`) and substring/list membership (`contains`).
- **Target Attributes or Primary State:** Inspect specific attributes (e.g., `equipment_running`, `aux_heat`, `fan`, `preset_mode`) or match the main state.
- **Realistic Jitter (`variance`):** Optionally inject random uniform noise (±W) on active loads so power curves exhibit natural electrical variations rather than artificial flat lines.

---

### 4. Native Riemann Sum Energy Accumulation (No Helper Clutter)
Eliminates the hassle of manually creating and managing Riemann sum integral helpers:
- **Direct Link to Power:** Point a Phantom Energy sensor directly at any power sensor (Phantom Power sensor, group sensor, or existing hardware sensor).
- **Dual Accumulation Engine:** Integrates on state change events and via a periodic 30-second background tick, ensuring steady-state loads increment continuously even without power fluctuations.
- **Persistent State Across Restarts:** Implements `RestoreEntity` so cumulative `kWh` is preserved across Home Assistant restarts and host reboots.
- **Energy Dashboard Ready:** Configured out of the box with `device_class: energy`, `state_class: total_increasing`, and `unit_of_measurement: kWh`.
- **Reset Service:** Includes the `phantom_power.reset_energy` service to zero or preset the cumulative accumulator.

---

### 5. Aggregate Power Groups
Combine individual power devices into unified load groups (e.g. by floor or category):
- **Real-Time Summation:** Aggregates member wattages live, automatically converting `kW` to `W` when required.
- **Diagnostic Attributes:** Exposes member wattage breakdowns (`members`), total member counts (`member_count`), and active loads (`active_members`).
- **Energy Pipeline Integration:** Point a Phantom Energy sensor directly at a Power Group sensor to generate clean, high-level energy metrics for the Home Assistant Energy tab (e.g., *Second Floor Lights Energy*, *Main Floor Lights Energy*).

---

### 6. Modern Core Standards & LGPL-3.0
- **Probatio Validation Engine:** Fully compatible with Home Assistant Core 2026.9+ Probatio validation, with transparent fallback to Voluptuous on older versions.
- **GNU LGPL-3.0 License:** Open source copyleft licensing ensuring user freedom while permitting standard linking.

---

## 📋 Quick Configuration Example

```yaml
phantom_power:
  power_sensors:
    # Dimmable light fixture
    - name: "Dining Room Lights Power"
      entity_id: light.dining_room
      power: 12.0
      min_power: 1.0
      standby_power: 0.0
      link_device: true

    # Smart plug with idle standby draw
    - name: "Coffee Maker Power"
      entity_id: switch.coffee_maker
      power: 1250.0
      standby_power: 1.8
      link_device: true

    # Multi-stage heat pump / thermostat
    - name: "Main Thermostat Power"
      entity_id: climate.main_thermostat
      standby_power: 0.0
      variance: 25.0
      link_device: true
      states:
        - attribute: aux_heat
          value: "on"
          power: 11000.0
        - attribute: equipment_running
          contains: "auxHeat1"
          power: 16000.0
        - attribute: equipment_running
          contains: "heatPump"
          power: 2000.0
        - attribute: fan
          value: "on"
          power: 50.0

  group_sensors:
    # Aggregated floor lighting wattage
    - name: "Main Floor Lights Power Group"
      entities:
        - sensor.dining_room_lights_power
        - sensor.kitchen_lights_power

  energy_sensors:
    # Cumulative kWh for Home Assistant Energy Dashboard
    - name: "Main Floor Lights Energy Group"
      power_sensor: sensor.main_floor_lights_power_group
      integration_method: trapezoidal
```

---

## 🛠️ Testing Checklist for Alpha Testers

1. **Visual Editor Webhook Sync:** Test clicking **Configure** in Home Assistant, launching the editor, adding a device, and clicking **Save & Sync to Home Assistant**.
2. **Dimmer Wattage Response:** Verify that dimming a light between 1% and 100% scales the reported power sensor smoothly between `min_power` and `power`.
3. **Multi-Stage Climate Rules:** Test state and attribute changes on complex devices (like thermostats or fans) to verify correct rule matching and variance jitter.
4. **Device Registry Linking:** Check that the generated power sensor is placed inside the target device's card under **Settings -> Devices & Services**.
5. **Continuous Energy Accumulation:** Let an active load run for 10–15 minutes and confirm that the linked energy sensor accumulates `kWh` steadily.
6. **State Restoration:** Restart Home Assistant and verify that accumulated `kWh` values remain intact.
