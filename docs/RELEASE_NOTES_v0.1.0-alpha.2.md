# 🚀 Phantom Power v0.1.0-alpha.2 — Synthetic Power & Energy Simulation for Home Assistant

> ### ⚠️ Alpha Release Notice
> **Phantom Power v0.1.0-alpha.2 continues testing of the synthetic power and energy tracking integration for Home Assistant.**
>
> Community testing and feedback are essential! If you encounter any bugs, state restoration regressions, or configuration issues, please open an issue with your configuration snippet and debug logs.

---

## 🌟 Highlights in v0.1.0-alpha.2

### 1. Device Registry Linking for Energy Sensors
Energy sensors now automatically link to their target device in the Home Assistant Device Registry:
- **Automatic Grouping:** Just like power sensors, `PhantomEnergySensor` now defaults `link_device: true`, resolving the parent device of its target power sensor and attaching itself directly.
- **No More "Ungrouped" Entities:** Energy sensors now cleanly appear on the device card alongside their associated power sensor and entity, rather than landing under "Ungrouped" on the Entities page.
- **Order-Independent Lifecycle:** Linking is resilient to entity startup order, automatically linking on startup and re-checking on subsequent state updates.

### 2. Clean Entity Discovery in the Visual Web Editor
- **Eliminated Entity Name Stuttering:** When discovering candidate entities from Home Assistant to propose in the visual editor, Phantom Power now inspects Home Assistant's Entity Registry (`has_entity_name` and sub-entity names).
- **No Repeated Device Names:** Prevents concatenating device and entity names (e.g. suggesting `Living Room Dimmer Power` rather than `Living Room Dimmer Living Room Light Power`).

### 3. Streamlined Developer Tooling & Scripts
- **Consolidated Helper Scripts:** Relocated `install` and `publish-release` into the `scripts/` directory with dynamic repository root discovery and active branch targeting.

### 4. Continuous Integration (CI) Workflows
- **Hassfest & HACS Validation:** Added GitHub Actions workflows verifying Hassfest integration requirements and HACS repository standards.

---

## 📋 What's Changed
- `feat(sensor)`: Support `link_device` (default: `true`) on `PhantomEnergySensor` to attach to parent devices in Home Assistant Device Registry.
- `feat(sensor)`: Clean candidate entity names in `config_flow` using entity registry `has_entity_name`.
- `build(scripts)`: Relocate `install` and `publish-release` to `scripts/` directory.
- `ci`: Add Hassfest and HACS GitHub Actions validation workflows.
- `docs`: Document `link_device` in `README.md` under `energy_sensors` configuration table.

---

## 📦 Upgrading to v0.1.0-alpha.2

### Via HACS
1. Open HACS in Home Assistant.
2. Select **Phantom Power** and click **Update**.
3. Restart Home Assistant to load the updated Python bytecode.

### Manual Installation
Sync the latest component files into your Home Assistant `/config` directory:
```bash
./scripts/install go /path/to/home-assistant/config
```
Then restart Home Assistant.
