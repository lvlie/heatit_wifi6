"""Climate platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import HeatitWiFi6API
from .const import DOMAIN, SENSORMODES, SENSORVALUES

_LOGGER = logging.getLogger(__name__)

OPERATING_MODE_OFF = 0
OPERATING_MODE_HEAT = 1
OPERATING_MODE_COOL = 2
OPERATING_MODE_ECO = 3

SETPOINT_BY_OPERATING_MODE = {
    OPERATING_MODE_HEAT: "heatingSetpoint",
    OPERATING_MODE_COOL: "coolingSetpoint",
    OPERATING_MODE_ECO: "ecoSetpoint",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 climate entity from a config entry."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HeatitWiFi6Thermostat(
                domain_data["coordinator"],
                domain_data["api"],
                entry.data[CONF_NAME],
                domain_data["device_id"],
            )
        ]
    )


class HeatitWiFi6Thermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a Heatit WiFi6 thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO]
    _attr_min_temp = 5
    _attr_max_temp = 40
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        api: HeatitWiFi6API,
        name: str,
        device_id: str,
    ) -> None:
        """Initialize the thermostat entity."""
        super().__init__(coordinator)
        self._api = api
        self._device_name = name
        self._device_id = device_id
        self._attr_unique_id = f"heatit_wifi6_{device_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry info."""
        firmware = None
        if self.coordinator.data:
            firmware = self.coordinator.data.get("firmware")
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Heatit",
            "model": "WiFi6 Thermostat",
            "sw_version": firmware,
        }

    @property
    def available(self) -> bool:
        """Return True if the coordinator was able to fetch data."""
        return self.coordinator.last_update_success

    def _parameters(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get("parameters") or {}

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature, picked according to active sensor mode."""
        data = self.coordinator.data
        if not data:
            return None
        sensor_mode = self._parameters().get("sensorMode")
        if sensor_mode == 0:
            return data.get("floorTemperature")
        if sensor_mode in (3, 4):
            return data.get("externalTemperature")
        return data.get("internalTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return setpoint corresponding to the active operating mode."""
        params = self._parameters()
        key = SETPOINT_BY_OPERATING_MODE.get(params.get("operatingMode"))
        if key is None:
            return None
        return params.get(key)

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF
        return self._heatit_operatingmode_to_hvac_mode(
            self._parameters().get("operatingMode")
        )

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        data = self.coordinator.data
        if not data:
            return HVACAction.OFF
        return self._heatit_state_to_hvac_action(data.get("state"))

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode (eco or none)."""
        if self._parameters().get("operatingMode") == OPERATING_MODE_ECO:
            return PRESET_ECO
        return PRESET_NONE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose detailed device parameters as state attributes."""
        data = self.coordinator.data
        if not data:
            return {}

        parameters = data.get("parameters", {})
        owd = parameters.get("OWD", {})
        network = data.get("network", {})

        return {
            "operating_mode": parameters.get("operatingMode"),
            "info_currentPower": data.get("currentPower"),
            "info_totalConsumption": data.get("totalConsumption"),
            "info_internalTemperature": data.get("internalTemperature"),
            "info_externalTemperature": data.get("externalTemperature"),
            "info_floorTemperature": data.get("floorTemperature"),
            "param_sensorMode": SENSORMODES.get(parameters.get("sensorMode"), "Unknown"),
            "param_sensorValue": SENSORVALUES.get(parameters.get("sensorValue"), "Unknown"),
            "param_heatingSetpoint": parameters.get("heatingSetpoint"),
            "param_coolingSetpoint": parameters.get("coolingSetpoint"),
            "param_ecoSetpoint": parameters.get("ecoSetpoint"),
            "param_internalMinimumTemperatureLimit": parameters.get("internalMinimumTemperatureLimit"),
            "param_internalMaximumTemperatureLimit": parameters.get("internalMaximumTemperatureLimit"),
            "param_floorMinimumTemperatureLimit": parameters.get("floorMinimumTemperatureLimit"),
            "param_floorMaximumTemperatureLimit": parameters.get("floorMaximumTemperatureLimit"),
            "param_externalMinimumTemperatureLimit": parameters.get("externalMinimumTemperatureLimit"),
            "param_externalMaximumTemperatureLimit": parameters.get("externalMaximumTemperatureLimit"),
            "param_internalCalibration": parameters.get("internalCalibration"),
            "param_floorCalibration": parameters.get("floorCalibration"),
            "param_externalCalibration": parameters.get("externalCalibration"),
            "param_regulationMode": parameters.get("regulationMode"),
            "param_temperatureControlHysteresis": parameters.get("temperatureControlHysteresis"),
            "param_temperatureDisplay": parameters.get("temperatureDisplay"),
            "param_activeDisplayBrightness": parameters.get("activeDisplayBrightness"),
            "param_standbyDisplayBrightness": parameters.get("standbyDisplayBrightness"),
            "param_actionAfterError": parameters.get("actionAfterError"),
            "param_powerRegulatorActiveTime": parameters.get("powerRegulatorActiveTime"),
            "param_sizeOfLoad": parameters.get("sizeOfLoad"),
            "param_disableButtons": parameters.get("disableButtons"),
            "owd_openWindowDetection": owd.get("openWindowDetection"),
            "owd_activeNow": owd.get("activeNow"),
            "net_ssid": network.get("SSID"),
            "net_mac": network.get("mac"),
            "net_ipAddress": network.get("ipAddress"),
            "net_wifiSignalStrength": network.get("wifiSignalStrength"),
            "net_status": network.get("status"),
            "hw_firmware": data.get("firmware"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.warning(
                "Cannot set target temperature for %s while device is OFF",
                self._device_name,
            )
            return

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.error("No temperature provided to async_set_temperature")
            return

        operating_mode = self._parameters().get("operatingMode")
        param = SETPOINT_BY_OPERATING_MODE.get(operating_mode)
        if param is None:
            _LOGGER.error(
                "Cannot set temperature: unsupported operating mode %s",
                operating_mode,
            )
            return

        if await self._api.set_parameter(param, temperature):
            # Optimistically update local state to keep the UI responsive.
            params = self.coordinator.data.setdefault("parameters", {})
            params[param] = temperature
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Switch between eco and normal heating modes."""
        if preset_mode == PRESET_ECO:
            await self._api.set_parameter("operatingMode", OPERATING_MODE_ECO)
        elif preset_mode in (PRESET_NONE, None):
            await self._api.set_parameter("operatingMode", OPERATING_MODE_HEAT)
        else:
            _LOGGER.warning("Unsupported preset_mode: %s", preset_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the device's HVAC mode."""
        operating_mode = self._hvac_mode_to_heatit_operatingmode(hvac_mode)
        if operating_mode is None:
            _LOGGER.error("Unsupported HVACMode: %s", hvac_mode)
            return
        if await self._api.set_parameter("operatingMode", operating_mode):
            await self.coordinator.async_request_refresh()

    @staticmethod
    def _hvac_mode_to_heatit_operatingmode(mode: HVACMode) -> int | None:
        if mode == HVACMode.OFF:
            return OPERATING_MODE_OFF
        if mode == HVACMode.HEAT:
            return OPERATING_MODE_HEAT
        if mode == HVACMode.COOL:
            return OPERATING_MODE_COOL
        return None

    @staticmethod
    def _heatit_operatingmode_to_hvac_mode(operating_mode: int | None) -> HVACMode | None:
        # 0 = Off, 1 = Heat, 2 = Cool, 3 = Eco (Heat with Eco setpoint)
        if operating_mode == OPERATING_MODE_OFF:
            return HVACMode.OFF
        if operating_mode in (OPERATING_MODE_HEAT, OPERATING_MODE_ECO):
            return HVACMode.HEAT
        if operating_mode == OPERATING_MODE_COOL:
            return HVACMode.COOL
        _LOGGER.error("Unknown operating mode from Heatit: %s", operating_mode)
        return None

    def _heatit_state_to_hvac_action(self, state: str | None) -> HVACAction | None:
        if state == "Idle":
            return HVACAction.OFF if self.hvac_mode == HVACMode.OFF else HVACAction.IDLE
        if state == "Heating":
            return HVACAction.HEATING
        if state == "Cooling":
            return HVACAction.COOLING
        _LOGGER.error("Unknown state from Heatit: %s", state)
        return None
