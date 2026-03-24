import asyncio
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    PRESET_ECO,
    PRESET_NONE,
)
from homeassistant.const import UnitOfTemperature, CONF_HOST, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from datetime import timedelta
from .const import SENSORMODES, SENSORVALUES, POLL_INTERVAL, DOMAIN
from .api import HeatitWiFi6API
from .exceptions import CannotConnect

PARAM_HEATING_NAME = "heatingSetpoint"
PARAM_COOLING_NAME = "coolingSetpoint"
errors = {}

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("async_setup_entry(): Heatit WiFi6")

    try:
        name = entry.data[CONF_NAME]
        host = entry.data[CONF_HOST]
        _LOGGER.info("Heatit WiFi6 async_setup_entry() name: %s, host: %s", name, host)

        domain_data = hass.data[DOMAIN][entry.entry_id]
        coordinator = domain_data["coordinator"]
        api = domain_data["api"]
        device_id = domain_data["device_id"]

        entity = HeatitWiFi6Thermostat(coordinator, hass, entry, api, name, device_id)
        # Don't update before add - let polling handle initial connection to speed up startup
        async_add_entities([entity], False)
        _LOGGER.info("Heatit WiFi6 %s has been added to the list of entities.", name)
        return True
    except Exception as err:
        _LOGGER.error(
            "Unknown error when trying setup the device: %s. Setup has been interrupted. (%s)",
            name,
            str(err),
        )
        return False

class HeatitWiFi6Thermostat(CoordinatorEntity, ClimateEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, hass, entry, api, name, device_id):
        super().__init__(coordinator)
        _LOGGER.debug("HeatitWiFi6Thermostat::__init__(): %s", name)
        self.hass = hass
        self.entry = entry
        self._api = api
        self._name = name
        self._device_id = device_id

        self._set_temperature_pending = False

    @property
    def unique_id(self):
        return f"heatit_wifi6_{self._device_id}"

    @property
    def device_info(self):
        hw_firmware = None
        if self.coordinator.data:
            hw_firmware = self.coordinator.data.get("firmware", None)
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._name,
            "manufacturer": "Heatit",
            "model": "WiFi6 Thermostat",
            "sw_version": hw_firmware,
        }

    @property
    def name(self):
        return None

    @property
    def icon(self):
        if self.hvac_mode == HVACMode.HEAT:
            return "mdi:radiator"
        else:
            return "mdi:radiator-off"

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        data = self.coordinator.data
        if not data:
            return None
        sensor_mode = data.get("parameters", {}).get("sensorMode", None)
        match sensor_mode:
            case 0:
                return data.get("floorTemperature", None)
            case 3 | 4:
                return data.get("externalTemperature", None)
            case _:
                return data.get("internalTemperature", None)

    @property
    def target_temperature(self):
        data = self.coordinator.data
        if not data:
            return None
        operating_mode = data.get("parameters", {}).get("operatingMode")
        match operating_mode:
            case 1:
                return data.get("parameters", {}).get("heatingSetpoint", None)
            case 2:
                return data.get("parameters", {}).get("coolingSetpoint", None)
            case 3:
                return data.get("parameters", {}).get("ecoSetpoint", None)
            case _:
                return None

    @property
    def hvac_mode(self):
        data = self.coordinator.data
        if not data:
            return HVACMode.OFF
        operating_mode = data.get("parameters", {}).get("operatingMode")
        return self._heatit_operatingmode_to_hvac_mode(operating_mode)

    @property
    def hvac_modes(self):
        match self.hvac_mode:
            case HVACMode.HEAT:
                return [HVACMode.OFF, HVACMode.HEAT]
            case HVACMode.COOL:
                return [HVACMode.OFF, HVACMode.COOL]
            case _:
                return [HVACMode.OFF, HVACMode.HEAT]

    @property
    def hvac_action(self):
        data = self.coordinator.data
        if not data:
            return HVACAction.OFF
        state = data.get("state")
        return self._heatit_state_to_hvac_action(state)

    @property
    def supported_features(self):
        return (
            ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
        )

    @property
    def preset_modes(self):
        return [PRESET_ECO, PRESET_NONE]

    @property
    def preset_mode(self):
        data = self.coordinator.data
        if not data:
            return PRESET_NONE
        operating_mode = data.get("parameters", {}).get("operatingMode")
        if operating_mode == 3:
            return PRESET_ECO
        return PRESET_NONE

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data:
            return {}

        # Expose operating_mode (raw value) and all the previous attributes
        attrs = {
            "operating_mode": data.get("parameters", {}).get("operatingMode", None),
            "info_currentPower": data.get("currentPower", None),
            "info_totalConsumption": data.get("totalConsumption", None),
            "info_internalTemperature": data.get("internalTemperature", None),
            "info_externalTemperature": data.get("externalTemperature", None),
            "info_floorTemperature": data.get("floorTemperature", None),
            "param_sensorMode": SENSORMODES.get(data.get("parameters", {}).get("sensorMode"), "Unknown"),
            "param_sensorValue": SENSORVALUES.get(data.get("parameters", {}).get("sensorValue"), "Unknown"),
            "param_heatingSetpoint": data.get("parameters", {}).get("heatingSetpoint", None),
            "param_coolingSetpoint": data.get("parameters", {}).get("coolingSetpoint", None),
            "param_ecoSetpoint": data.get("parameters", {}).get("ecoSetpoint", None),
            "param_internalMinimumTemperatureLimit": data.get("parameters", {}).get("internalMinimumTemperatureLimit", None),
            "param_internalMaximumTemperatureLimit": data.get("parameters", {}).get("internalMaximumTemperatureLimit", None),
            "param_floorMinimumTemperatureLimit": data.get("parameters", {}).get("floorMinimumTemperatureLimit", None),
            "param_floorMaximumTemperatureLimit": data.get("parameters", {}).get("floorMaximumTemperatureLimit", None),
            "param_externalMinimumTemperatureLimit": data.get("parameters", {}).get("externalMinimumTemperatureLimit", None),
            "param_externalMaximumTemperatureLimit": data.get("parameters", {}).get("externalMaximumTemperatureLimit", None),
            "param_internalCalibration": data.get("parameters", {}).get("internalCalibration", None),
            "param_floorCalibration": data.get("parameters", {}).get("floorCalibration", None),
            "param_externalCalibration": data.get("parameters", {}).get("externalCalibration", None),
            "param_regulationMode": data.get("parameters", {}).get("regulationMode", None),
            "param_temperatureControlHysteresis": data.get("parameters", {}).get("temperatureControlHysteresis", None),
            "param_temperatureDisplay": data.get("parameters", {}).get("temperatureDisplay", None),
            "param_activeDisplayBrightness": data.get("parameters", {}).get("activeDisplayBrightness", None),
            "param_standbyDisplayBrightness": data.get("parameters", {}).get("standbyDisplayBrightness", None),
            "param_actionAfterError": data.get("parameters", {}).get("actionAfterError", None),
            "param_powerRegulatorActiveTime": data.get("parameters", {}).get("powerRegulatorActiveTime", None),
            "param_sizeOfLoad": data.get("parameters", {}).get("sizeOfLoad", None),
            "param_disableButtons": data.get("parameters", {}).get("disableButtons", None),
            "owd_openWindowDetection": data.get("parameters", {}).get("OWD", {}).get("openWindowDetection", None),
            "owd_activeNow": data.get("parameters", {}).get("OWD", {}).get("activeNow", None),
            "net_ssid": data.get("network", {}).get("SSID", None),
            "net_mac": data.get("network", {}).get("mac", None),
            "net_ipAddress": data.get("network", {}).get("ipAddress", None),
            "net_wifiSignalStrength": data.get("network", {}).get("wifiSignalStrength", None),
            "net_status": data.get("network", {}).get("status", None),
            "hw_firmware": data.get("firmware", None),
        }
        return attrs

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.coordinator.last_update_success

    async def async_set_temperature(self, **kwargs):
        # If the Heatit device is switched off don't change the target temperatures.
        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.info(
                "async_set_temperature(): The device %s is switched off. Target temperature can changed only when device is on.",
                self._name,
            )
            await self.coordinator.async_request_refresh()
            self.hass.components.persistent_notification.create(
                "Target temperature can changed only when Heatit WiFi6 device is ON.",
                title="Heatif WiFi6 Thermostat",
            )
            return
        temperature = kwargs.get("temperature")
        if temperature is None:
            _LOGGER.error(
                "async_set_temperature(): A new target temperature not set/known. Change target value aborted."
            )
            return
        self._set_temperature_pending = True
        data = self.coordinator.data
        if not data:
            self._set_temperature_pending = False
            return
        operating_mode = data.get("parameters", {}).get("operatingMode")
        match operating_mode:
            case 1:
                param = "heatingSetpoint"
            case 2:
                param = "coolingSetpoint"
            case 3:
                param = "ecoSetpoint"
            case _:
                self._set_temperature_pending = False
                return
        if await self._api.set_parameter(param, temperature):
            # Optimistically update the coordinator data with the newly set value
            # This is optional but helps with responsiveness if we don't want to rely
            # entirely on the refresh cycle
            self.coordinator.data.get("parameters", {})[param] = temperature
            self._set_temperature_pending = False
            await self.coordinator.async_request_refresh()
        self._set_temperature_pending = False  # also here, if set_parameter() fails.

    async def async_set_preset_mode(self, preset_mode):
        # Eco: operatingMode=3, None (normal): operatingMode=1
        if preset_mode == PRESET_ECO:
            await self._api.set_parameter("operatingMode", 3)
        elif preset_mode == PRESET_NONE or preset_mode is None:
            await self._api.set_parameter("operatingMode", 1)
        else:
            _LOGGER.warning(
                "async_set_preset_mode(): Unsupported preset_mode: %s", str(preset_mode)
            )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode, force=False):
        if not force and hvac_mode not in self.hvac_modes:
            _LOGGER.error("async_set_hvac_mode(): unsupported HVACMode: %s", str(hvac_mode))
            return
        if await self._api.set_parameter(
            "operatingMode", self._hvac_mode_to_heatit_operatingmode(hvac_mode)
        ):
            await self.coordinator.async_request_refresh()

    def _hvac_mode_to_heatit_operatingmode(self, mode):
        match mode:
            case HVACMode.OFF:
                return 0
            case HVACMode.HEAT:
                return 1
            case HVACMode.COOL:
                return 2
            case _:
                _LOGGER.error(
                    "_hvac_mode_to_heatit_operatingmode(): Unsupported mode requested from Home Assistant to Heatit: %s",
                    str(mode),
                )
                return -1

    async def _heatit_operatingmode_to_hvac_mode(self, operatingmode):
        # 0 = Off, 1 = Heat, 2 = Cool, 3 = Eco (Heat but using Eco setpoint)
        match operatingmode:
            case 0:
                return HVACMode.OFF
            case 1:
                return HVACMode.HEAT
            case 2:
                return HVACMode.COOL
            case 3:
                return HVACMode.HEAT
            case _:
                _LOGGER.error(
                    "_heatit_operatingmode_to_hvac_mode(): Unknown state from Heatit: %s",
                    str(operatingmode),
                )
                return None

    def _heatit_state_to_hvac_action(self, state):
        match state:
            case "Idle":
                return (
                    HVACAction.OFF
                    if self.hvac_mode == HVACMode.OFF
                    else HVACAction.IDLE
                )
            case "Heating":
                return HVACAction.HEATING
            case "Cooling":
                return HVACAction.COOLING
            case _:
                _LOGGER.error(
                    "_heatit_state_to_hvac_action(): Unknown operation mode from Heatit: %s",
                    str(state),
                )
                return None
