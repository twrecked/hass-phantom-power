# 🚀 Phantom Power v0.1.0-alpha.1 — Synthetic Power & Energy Simulation for Home Assistant

> ### ⚠️ Alpha Release Notice
> **Phantom Power v0.1.0-alpha.1 is the initial alpha release of a dedicated Home Assistant integration for synthesizing power (Watts) and energy (kWh) metrics for non-reporting devices, dimmers, appliances, and aggregated groups.**
>
> Community testing and feedback are essential! If you encounter any bugs, state restoration regressions, or configuration issues, please open an issue with your configuration snippet and debug logs.

---

## 🌟 Highlights

### 1. Virtual Power Sensors with Linear Dimmer Scaling
Associate realistic wattage measurements with any existing Home Assistant entity:
- **Dimmable Lights**: Automatically computes real-time wattage based on light `brightness` (0–255), scaling linearly between `min_power` and `power`.
- **Fans & Speed Controllers**: Scales wattage linearly with the `percentage` attribute (0–100%).
- **On/Off Appliances & Outlets**: Reports rated wattage when active and `standby_power` (e.g. 0.5–2W) when switched off or idling.
- **Configurable Device Linking**: Set `link_device: true` to automatically link the synthetic power sensor directly to the source entity's existing device in Home Assistant's Device Registry, making it show up directly on the device card.

---

### 2. Native Riemann Sum Energy Accumulation (No Helper Clutter)
Eliminates the hassle of manually creating and managing Riemann sum integral helpers:
- **Direct Link to Power**: Point a Phantom Energy sensor directly at any power sensor (Phantom Power sensor, group sensor, or existing hardware sensor).
- **Dual Accumulation Engine**: Integrates on state change events and via a periodic 30-second background tick, ensuring steady-state loads increment continuously even without power fluctuations.
- **Persistent State Across Restarts**: Implements `RestoreEntity` so cumulative `kWh` is preserved across Home Assistant restarts and host reboots.
- **Energy Dashboard Ready**: Configured out of the box with `device_class: energy`, `state_class: total_increasing`, and `unit_of_measurement: kWh`.
- **Reset Service**: Includes the `phantom_power.reset_energy` service to zero or preset the cumulative accumulator.

---

### 3. Aggregate Power Groups
Combine individual power devices into unified load groups:
- **Real-Time Summation**: Aggregates member wattages live, automatically converting `kW` to `W` when required.
- **Diagnostic Attributes**: Exposes member wattage breakdowns (`members`), total member counts (`member_count`), and active loads (`active_members`).
- **Energy Pipeline Integration**: Point a Phantom Energy sensor directly at a Power Group sensor to generate clean, high-level energy metrics for the Home Assistant Energy tab (e.g., *All Lighting Energy*, *HVAC & Fans Energy*).

---

### 4. Zero-Friction Configuration & Hot Reloading
- **YAML & Config Flow**: Configure devices cleanly in `/config/phantom_power.yaml` or directly in `configuration.yaml`.
- **Hot Reloading**: Update your configuration file and call `phantom_power.reload` to apply changes instantly without restarting Home Assistant.
- **HACS Ready**: Ready for custom repository installation via HACS with `"render_readme": true`.

---

## 📋 Quick Configuration Example

```yaml
phantom_power:
  power_sensors:
    # Dimmable dining room fixture
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

  group_sensors:
    # Aggregated lighting wattage
    - name: "All Lights Power Group"
      entities:
        - sensor.dining_room_lights_power
        - sensor.kitchen_lights_power

  energy_sensors:
    # Cumulative kWh for the Home Assistant Energy tab
    - name: "All Lights Energy Group"
      power_sensor: sensor.all_lights_power_group
      integration_method: trapezoidal
```

---

## 🛠️ Testing Checklist for Alpha Testers

1. **Dimmer Wattage Response**: Verify that dimming a light between 1% and 100% scales the reported power sensor smoothly between `min_power` and `power`.
2. **Device Registry Linking**: Check whether the generated power sensor is placed inside the target device's card under **Settings -> Devices & Services**.
3. **Continuous Energy Accumulation**: Let an active load run for 10–15 minutes and confirm that the linked energy sensor accumulates `kWh` steadily.
4. **State Restoration**: Restart Home Assistant and verify that accumulated `kWh` values remain intact.
5. **Group Summation**: Turn individual member lights on and off to verify that the group power sensor updates its sum and active member count.
