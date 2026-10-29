/**
 * Phantom Power Editor - Vue 3 Application
 */

const { createApp, ref, computed, onMounted, watch } = Vue;

function slugify(text) {
  if (!text) return "";
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "_")
    .replace(/[^\w\-]+/g, "")
    .replace(/\-\-+/g, "_");
}

createApp({
  setup() {
    const callbackUrl = ref(window.INITIAL_DATA?.callbackUrl || "");
    const token = ref(window.INITIAL_DATA?.token || "");
    const groupName = ref(window.INITIAL_DATA?.groupName || "phantom_power.yaml");
    const activeTab = ref("available");
    const isSaving = ref(false);

    // Data models
    const powerSensors = ref([]);
    const groupSensors = ref([]);
    const energySensors = ref([]);
    const candidateEntities = ref(window.INITIAL_DATA?.candidateEntities || []);
    const rawYamlPreview = ref("");

    // Filtering
    const searchQuery = ref("");
    const filterDomain = ref("all");

    // Modals
    const showTrackModal = ref(false);
    const isEditingExisting = ref(false);
    const editingPowerIndex = ref(null);
    const trackForm = ref({
      mode: "simple", // "simple" or "rules"
      name: "",
      entity_id: "",
      power: 12.0,
      min_power: 0.0,
      standby_power: 0.0,
      variance: 0.0,
      link_device: true,
      states: [],
      create_energy: true,
      target_group: "",
      new_group_name: "",
    });

    const showGroupModal = ref(false);
    const editingGroupIndex = ref(null);
    const groupForm = ref({
      name: "",
      entities: [],
      create_energy_group: false,
    });

    const showEnergyModal = ref(false);
    const editingEnergyIndex = ref(null);
    const energyForm = ref({
      name: "",
      power_sensor: "",
      integration_method: "trapezoidal",
    });

    // Toast notifications
    const toast = ref(null);
    const showToast = (message, type = "success") => {
      toast.value = { message, type };
      setTimeout(() => {
        if (toast.value?.message === message) {
          toast.value = null;
        }
      }, 3500);
    };

    // Load and decode data on mount
    onMounted(() => {
      let initialYaml = window.INITIAL_DATA?.initialYaml || "";

      // Inspect URL hash for #data=...
      if (window.location.hash.startsWith("#data=")) {
        try {
          const hashData = window.location.hash.substring(6);
          const raw = atob(hashData);
          try {
            const parsed = JSON.parse(raw);
            if (parsed.yaml) initialYaml = parsed.yaml;
            if (parsed.entities && parsed.entities.length > 0) {
              candidateEntities.value = parsed.entities;
            }
          } catch {
            initialYaml = raw;
          }
        } catch (err) {
          console.warn("Could not decode hash data:", err);
        }
      }

      if (initialYaml) {
        parseIncomingYaml(initialYaml);
      } else {
        updateYamlPreview();
      }

      if (candidateEntities.value.length === 0) {
        activeTab.value = "power";
      }
    });

    // Parse YAML into internal collections
    const parseIncomingYaml = (yamlText) => {
      try {
        const obj = jsyaml.load(yamlText) || {};
        const root = obj.phantom_power || obj;

        powerSensors.value = (root.power_sensors || []).map((s) => ({
          name: s.name || "",
          entity_id: s.entity_id || "",
          power: Number(s.power || 0),
          min_power: Number(s.min_power || 0),
          standby_power: Number(s.standby_power || 0),
          variance: Number(s.variance || 0),
          link_device: s.link_device !== false,
          states: Array.isArray(s.states) ? [...s.states] : [],
        }));

        groupSensors.value = (root.group_sensors || []).map((g) => ({
          name: g.name || "",
          entities: Array.isArray(g.entities) ? [...g.entities] : [],
        }));

        energySensors.value = (root.energy_sensors || []).map((e) => ({
          name: e.name || "",
          power_sensor: e.power_sensor || "",
          integration_method: e.integration_method || "trapezoidal",
        }));

        updateYamlPreview();
      } catch (err) {
        console.error("Error parsing YAML:", err);
        showToast("Error parsing existing YAML: " + err.message, "error");
      }
    };

    // Build YAML string from internal collections
    const generateYamlObject = () => {
      const data = {};
      if (powerSensors.value.length > 0) {
        data.power_sensors = powerSensors.value.map((s) => {
          const item = {
            name: s.name,
            entity_id: s.entity_id,
          };

          if (s.states && s.states.length > 0) {
            item.standby_power = Number(s.standby_power || 0);
            if (s.variance) item.variance = Number(s.variance);
            if (s.link_device === false) item.link_device = false;
            item.states = s.states;
          } else {
            item.power = Number(s.power || 0);
            if (s.min_power) item.min_power = Number(s.min_power);
            if (s.standby_power) item.standby_power = Number(s.standby_power);
            if (s.variance) item.variance = Number(s.variance);
            if (s.link_device === false) item.link_device = false;
          }
          return item;
        });
      }
      if (groupSensors.value.length > 0) {
        data.group_sensors = groupSensors.value.map((g) => ({
          name: g.name,
          entities: g.entities,
        }));
      }
      if (energySensors.value.length > 0) {
        data.energy_sensors = energySensors.value.map((e) => {
          const item = {
            name: e.name,
            power_sensor: e.power_sensor,
          };
          if (e.integration_method && e.integration_method !== "trapezoidal") {
            item.integration_method = e.integration_method;
          }
          return item;
        });
      }

      return { phantom_power: data };
    };

    const updateYamlPreview = () => {
      try {
        const obj = generateYamlObject();
        rawYamlPreview.value = jsyaml.dump(obj, { indent: 2, lineWidth: -1 });
      } catch (err) {
        console.error("Error generating YAML:", err);
      }
    };

    const onYamlEdited = () => {
      try {
        const obj = jsyaml.load(rawYamlPreview.value) || {};
        const root = obj.phantom_power || obj;
        if (root.power_sensors) powerSensors.value = root.power_sensors;
        if (root.group_sensors) groupSensors.value = root.group_sensors;
        if (root.energy_sensors) energySensors.value = root.energy_sensors;
      } catch {
        // User may be typing invalid YAML
      }
    };

    // Candidate entity helper methods
    const isEntityTracked = (entityId) => {
      return powerSensors.value.some((s) => s.entity_id === entityId);
    };

    const getTrackedWattage = (entityId) => {
      const match = powerSensors.value.find((s) => s.entity_id === entityId);
      if (!match) return "0W";
      if (match.states && match.states.length > 0) {
        return `${match.states.length} rules`;
      }
      return `${match.power}W`;
    };

    const currentEntityAttributes = computed(() => {
      const targetId = trackForm.value.entity_id;
      const found = candidateEntities.value.find((e) => e.entity_id === targetId);
      return found?.attributes || [];
    });

    const filteredCandidates = computed(() => {
      return candidateEntities.value.filter((ent) => {
        if (filterDomain.value !== "all" && ent.domain !== filterDomain.value) {
          return false;
        }
        if (searchQuery.value) {
          const q = searchQuery.value.toLowerCase();
          const matchName = (ent.name || "").toLowerCase().includes(q);
          const matchId = (ent.entity_id || "").toLowerCase().includes(q);
          if (!matchName && !matchId) return false;
        }
        return true;
      });
    });

    // Tracking Modal Handlers
    const openTrackModal = (entity) => {
      isEditingExisting.value = false;
      editingPowerIndex.value = null;

      const isClimate = entity.domain === "climate";
      let defaultPower = 12.0;
      let minPower = 0.0;
      let defaultStates = [];

      if (isClimate) {
        defaultPower = 0;
        defaultStates = [
          { attribute: "equipment_running", condition: "contains", value: "auxHeat", power: 11000 },
          { attribute: "equipment_running", condition: "contains", value: "heatPump", power: 2500 },
          { attribute: "equipment_running", condition: "contains", value: "compCool", power: 2200 },
          { attribute: "fan", condition: "equals", value: "on", power: 60 },
        ];
      } else if (entity.domain === "light") {
        defaultPower = 12.0;
        minPower = entity.is_dimmable ? 1.0 : 0.0;
      } else if (entity.domain === "fan") {
        defaultPower = 65.0;
        minPower = 12.0;
      } else if (entity.domain === "switch") {
        defaultPower = 100.0;
      }

      trackForm.value = {
        mode: isClimate ? "rules" : "simple",
        name: `${entity.name || entity.entity_id} Power`,
        entity_id: entity.entity_id,
        power: defaultPower,
        min_power: minPower,
        standby_power: 0.0,
        variance: isClimate ? 25.0 : 0.0,
        link_device: true,
        states: defaultStates,
        create_energy: true,
        target_group: "",
        new_group_name: "",
      };

      showTrackModal.value = true;
    };

    const editTrackedEntity = (entityId) => {
      const idx = powerSensors.value.findIndex((s) => s.entity_id === entityId);
      if (idx !== -1) editPowerSensor(idx);
    };

    const editPowerSensor = (idx) => {
      const s = powerSensors.value[idx];
      editingPowerIndex.value = idx;
      isEditingExisting.value = true;

      const hasStates = Array.isArray(s.states) && s.states.length > 0;
      const formattedStates = hasStates
        ? s.states.map((r) => ({
            attribute: r.attribute || "",
            condition: r.contains !== undefined ? "contains" : "equals",
            value: r.contains !== undefined ? r.contains : (r.value !== undefined ? r.value : r.state || ""),
            power: Number(r.power || 0),
          }))
        : [];

      trackForm.value = {
        mode: hasStates ? "rules" : "simple",
        name: s.name,
        entity_id: s.entity_id,
        power: Number(s.power || 0),
        min_power: Number(s.min_power || 0),
        standby_power: Number(s.standby_power || 0),
        variance: Number(s.variance || 0),
        link_device: s.link_device !== false,
        states: formattedStates,
        create_energy: false,
        target_group: "",
        new_group_name: "",
      };
      showTrackModal.value = true;
    };

    const openManualPowerModal = () => {
      isEditingExisting.value = false;
      editingPowerIndex.value = null;
      trackForm.value = {
        mode: "simple",
        name: "New Power Sensor",
        entity_id: "",
        power: 10.0,
        min_power: 0.0,
        standby_power: 0.0,
        variance: 0.0,
        link_device: true,
        states: [],
        create_energy: true,
        target_group: "",
        new_group_name: "",
      };
      showTrackModal.value = true;
    };

    // Rule helpers for Multi-State mode
    const addRule = () => {
      trackForm.value.states.push({
        attribute: "equipment_running",
        condition: "contains",
        value: "",
        power: 1000,
      });
    };

    const deleteRule = (idx) => {
      trackForm.value.states.splice(idx, 1);
    };

    const moveRuleUp = (idx) => {
      if (idx > 0) {
        const item = trackForm.value.states.splice(idx, 1)[0];
        trackForm.value.states.splice(idx - 1, 0, item);
      }
    };

    const moveRuleDown = (idx) => {
      if (idx < trackForm.value.states.length - 1) {
        const item = trackForm.value.states.splice(idx, 1)[0];
        trackForm.value.states.splice(idx + 1, 0, item);
      }
    };

    const saveTrackForm = () => {
      if (!trackForm.value.name || !trackForm.value.entity_id) {
        showToast("Please provide both name and entity_id", "error");
        return;
      }

      const isRulesMode = trackForm.value.mode === "rules";
      const powerEntry = {
        name: trackForm.value.name,
        entity_id: trackForm.value.entity_id,
        link_device: trackForm.value.link_device,
        standby_power: Number(trackForm.value.standby_power || 0),
        variance: Number(trackForm.value.variance || 0),
      };

      if (isRulesMode) {
        powerEntry.states = trackForm.value.states.map((r) => {
          const ruleObj = { power: Number(r.power || 0) };
          if (r.attribute && r.attribute.trim()) {
            ruleObj.attribute = r.attribute.trim();
          }
          if (r.condition === "contains") {
            ruleObj.contains = r.value;
          } else {
            ruleObj.value = r.value;
          }
          return ruleObj;
        });
      } else {
        powerEntry.power = Number(trackForm.value.power || 0);
        powerEntry.min_power = Number(trackForm.value.min_power || 0);
      }

      if (isEditingExisting.value && editingPowerIndex.value !== null) {
        powerSensors.value[editingPowerIndex.value] = powerEntry;
      } else {
        powerSensors.value.push(powerEntry);

        // Auto-create companion energy sensor
        if (trackForm.value.create_energy) {
          const powerSensorId = `sensor.${slugify(trackForm.value.name)}`;
          const energyName = trackForm.value.name.replace(/\s*Power$/, "") + " Energy";
          energySensors.value.push({
            name: energyName,
            power_sensor: powerSensorId,
            integration_method: "trapezoidal",
          });
        }

        // Add to group
        const powerSensorId = `sensor.${slugify(trackForm.value.name)}`;
        if (trackForm.value.target_group === "__NEW__" && trackForm.value.new_group_name) {
          groupSensors.value.push({
            name: trackForm.value.new_group_name,
            entities: [powerSensorId],
          });
        } else if (trackForm.value.target_group) {
          const grp = groupSensors.value.find((g) => g.name === trackForm.value.target_group);
          if (grp && !grp.entities.includes(powerSensorId)) {
            grp.entities.push(powerSensorId);
          }
        }
      }

      updateYamlPreview();
      showTrackModal.value = false;
      showToast(`Saved power sensor: ${powerEntry.name}`);
    };

    const deletePowerSensor = (idx) => {
      const removed = powerSensors.value.splice(idx, 1)[0];
      updateYamlPreview();
      showToast(`Removed: ${removed.name}`);
    };

    // Group Modal Handlers
    const openGroupModal = (idx = null) => {
      editingGroupIndex.value = idx;
      if (idx !== null) {
        const g = groupSensors.value[idx];
        groupForm.value = {
          name: g.name,
          entities: [...(g.entities || [])],
          create_energy_group: false,
        };
      } else {
        groupForm.value = {
          name: "All Lights Power Group",
          entities: powerSensors.value.map((s) => `sensor.${slugify(s.name)}`),
          create_energy_group: true,
        };
      }
      showGroupModal.value = true;
    };

    const saveGroupForm = () => {
      if (!groupForm.value.name) {
        showToast("Please provide a group name", "error");
        return;
      }

      const groupEntry = {
        name: groupForm.value.name,
        entities: [...groupForm.value.entities],
      };

      if (editingGroupIndex.value !== null) {
        groupSensors.value[editingGroupIndex.value] = groupEntry;
      } else {
        groupSensors.value.push(groupEntry);

        if (groupForm.value.create_energy_group) {
          const groupPowerId = `sensor.${slugify(groupEntry.name)}`;
          const energyName = groupEntry.name.replace(/\s*Power\s*Group$/i, "") + " Energy Group";
          energySensors.value.push({
            name: energyName,
            power_sensor: groupPowerId,
            integration_method: "trapezoidal",
          });
        }
      }

      updateYamlPreview();
      showGroupModal.value = false;
      showToast(`Saved group: ${groupEntry.name}`);
    };

    const deleteGroupSensor = (idx) => {
      const removed = groupSensors.value.splice(idx, 1)[0];
      updateYamlPreview();
      showToast(`Removed group: ${removed.name}`);
    };

    // Energy Modal Handlers
    const openEnergyModal = (idx = null) => {
      editingEnergyIndex.value = idx;
      if (idx !== null) {
        const e = energySensors.value[idx];
        energyForm.value = { ...e };
      } else {
        energyForm.value = {
          name: "New Energy Sensor",
          power_sensor: powerSensors.value.length > 0 ? `sensor.${slugify(powerSensors.value[0].name)}` : "",
          integration_method: "trapezoidal",
        };
      }
      showEnergyModal.value = true;
    };

    const saveEnergyForm = () => {
      if (!energyForm.value.name || !energyForm.value.power_sensor) {
        showToast("Please provide both name and target power sensor", "error");
        return;
      }

      if (editingEnergyIndex.value !== null) {
        energySensors.value[editingEnergyIndex.value] = { ...energyForm.value };
      } else {
        energySensors.value.push({ ...energyForm.value });
      }

      updateYamlPreview();
      showEnergyModal.value = false;
      showToast(`Saved energy sensor: ${energyForm.value.name}`);
    };

    const deleteEnergySensor = (idx) => {
      const removed = energySensors.value.splice(idx, 1)[0];
      updateYamlPreview();
      showToast(`Removed energy sensor: ${removed.name}`);
    };

    // Save & Return via Home Assistant Webhook Callback
    const saveAndReturn = async () => {
      if (!callbackUrl.value) {
        downloadYaml();
        return;
      }

      isSaving.value = true;
      updateYamlPreview();

      try {
        const res = await fetch("/api/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            callback_url: callbackUrl.value,
            token: token.value,
            yaml: rawYamlPreview.value,
          }),
        });

        const data = await res.json();
        if (res.ok && data.ok) {
          showToast("✓ Successfully saved and reloaded in Home Assistant!", "success");
        } else {
          showToast("Save failed: " + (data.error || "Unknown error"), "error");
        }
      } catch (err) {
        showToast("Error connecting to editor server: " + err.message, "error");
      } finally {
        isSaving.value = false;
      }
    };

    const downloadYaml = () => {
      updateYamlPreview();
      const blob = new Blob([rawYamlPreview.value], { type: "text/yaml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "phantom_power.yaml";
      a.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded phantom_power.yaml");
    };

    const copyYaml = () => {
      updateYamlPreview();
      navigator.clipboard.writeText(rawYamlPreview.value);
      showToast("Copied YAML to clipboard!");
    };

    return {
      callbackUrl,
      token,
      groupName,
      activeTab,
      isSaving,
      powerSensors,
      groupSensors,
      energySensors,
      candidateEntities,
      rawYamlPreview,
      searchQuery,
      filterDomain,
      filteredCandidates,
      currentEntityAttributes,
      showTrackModal,
      isEditingExisting,
      trackForm,
      showGroupModal,
      editingGroupIndex,
      groupForm,
      showEnergyModal,
      editingEnergyIndex,
      energyForm,
      toast,
      slugify,
      isEntityTracked,
      getTrackedWattage,
      openTrackModal,
      editTrackedEntity,
      editPowerSensor,
      openManualPowerModal,
      addRule,
      deleteRule,
      moveRuleUp,
      moveRuleDown,
      saveTrackForm,
      deletePowerSensor,
      openGroupModal,
      saveGroupForm,
      deleteGroupSensor,
      openEnergyModal,
      saveEnergyForm,
      deleteEnergySensor,
      onYamlEdited,
      saveAndReturn,
      downloadYaml,
      copyYaml,
    };
  },
}).mount("#app");
