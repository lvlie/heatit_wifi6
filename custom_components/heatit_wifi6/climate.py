import asyncio
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode, HVACAction
from homeassistant.const import UnitOfTemperature, CONF_HOST, CONF_NAME
from datetime import timedelta
from .const import SENSORMODES, SENSORVALUES, POLL_INTERVAL
from .api import HeatitWiFi6API
from .exceptions import CannotConnect

PARAM_HEATING_NAME = "heatingSetpoint"
PARAM_COOLING_NAME = "coolingSetpoint"
errors = {}

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("async_setup_entry(): Heatit WiFi6")

    try:
        name = entry.data[CONF_NAME]  # Get name from UI config
        host = entry.data[CONF_HOST]  # Get host from UI config
        _LOGGER.info("Heatit WiFi6 async_setup_entry() name: %s, host: %s", name, host)

        api = HeatitWiFi6API(host)
        device_id = await api.get_device_id()
        _LOGGER.debug("Name: %s, device_id: %s", name, device_id)
        if device_id == "unknown": raise CannotConnect

        entity = HeatitWiFi6Thermostat(hass, entry, api, name, device_id)
        async_add_entities([entity], True)
        _LOGGER.debug("Heatit WiFi6 %s has been added to the list of entities.", name)
        return True
    except CannotConnect:
        _LOGGER.error("Connect failed to the device: %s", name)
        return False  # =>failed, don't try again.    
    except Exception as err:
        _LOGGER.error("Unknown error when trying setup the device: %s. Setup has been interrupted. (%s)", name, str(err))
        return False  # =>failed, don't try again.

class HeatitWiFi6Thermostat(ClimateEntity):
    attr_has_entity_name = True
    should_poll = False  # Turn polling on after entity is ready for working.
    SCAN_INTERVAL = timedelta(minutes=POLL_INTERVAL)
    
    def __init__(self, hass, entry, api, name, device_id):
        _LOGGER.debug("HeatitWiFi6Thermostat::__init__(): %s", name)
        self.hass = hass
        self.entry = entry
        self._api = api
        self._name = name
        self._device_id = device_id

        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        self._temperature = None
        self._set_temperature_pending = False

        self._info_currentPower = None
        self._info_totalConsumption = None
        self._info_internalTemperature = None
        self._info_externalTemperature = None
        self._info_floorTemperature = None
        self._param_sensorMode = None
        self._param_sensorValue = None
        self._param_heatingSetpoint = None
        self._param_coolingSetpoint = None
        self._param_ecoSetpoint = None
        self._param_internalMinimumTemperatureLimit = None
        self._param_internalMaximumTemperatureLimit = None
        self._param_floorMinimumTemperatureLimit = None
        self._param_floorMaximumTemperatureLimit = None
        self._param_externalMinimumTemperatureLimit = None
        self._param_externalMaximumTemperatureLimit = None
        self._param_internalCalibration = None
        self._param_floorCalibration = None
        self._param_externalCalibration = None
        self._param_regulationMode = None
        self._param_temperatureControlHysteresis = None
        self._param_temperatureDisplay = None
        self._param_activeDisplayBrightness = None
        self._param_standbyDisplayBrightness = None
        self._param_actionAfterError = None
        self._param_powerRegulatorActiveTime = None
        self._param_operatingMode = None
        self._param_sizeOfLoad = None
        self._param_disableButtons = None
        self._owd_openWindowDetection = None
        self._owd_activeNow = None    
        self._net_ssid = None
        self._net_mac = None
        self._net_ipAddress = None
        self._net_wifiSignalStrength = None
        self._net_status = None
        self._hw_firmware = None
        
        self._available = True

    # HA call this when the entity is ready and added to the HA entity list.
    async def async_added_to_hass(self):
        await self.async_update()    # auto poll off, start polling here..
        self.should_poll = True     # turn on auto polling.
        _LOGGER.info("async_added_to_hass(): Heatit WiFi6 integration is ready and polling enabled.")

    async def async_update(self):
        data = await self._api.get_status()
        if data:
            self._available = True
            match data.get("parameters",{}).get("sensorMode", None):              # return temp depending on used sensor (sensorMode)
                case 0: self._temperature = data.get("floorTemperature", None)         # mode: F
                case 3 | 4: self._temperature = data.get("externalTemperature", None)  # mode: A2, A2F
                case _: self._temperature = data.get("internalTemperature", None)      # all other modes: A, AF, PWER
            self._param_operatingMode = data.get("parameters").get("operatingMode")
            self._hvac_mode = await self._heatit_operatingmode_to_hvac_mode(self._param_operatingMode)
            self._hvac_action =  await self._heatit_state_to_hvac_action(data.get("state"))  # note: _hvac_mode should be set before _hvac_action.
            if not self._set_temperature_pending:  # refresh target temperatures only when no change pending.
                self._param_coolingSetpoint = data.get("parameters", {}).get("coolingSetpoint", None)
                self._param_heatingSetpoint = data.get("parameters", {}).get("heatingSetpoint", None)
                self._param_ecoSetpoint = data.get("parameters", {}).get("ecoSetpoint", None)

            self._info_currentPower = data.get("currentPower", None)
            self._info_totalConsumption = data.get("totalConsumption", None)
            self._info_internalTemperature = data.get("internalTemperature", None)
            self._info_externalTemperature = data.get("externalTemperature", None)
            self._info_floorTemperature = data.get("floorTemperature", None)

            self._param_sensorMode = data.get("parameters",{}).get("sensorMode", None)
            self._param_sensorValue = data.get("parameters",{}).get("sensorValue", None)
            self._param_internalMinimumTemperatureLimit = data.get("parameters",{}).get("internalMinimumTemperatureLimit", None)
            self._param_internalMaximumTemperatureLimit = data.get("parameters",{}).get("internalMaximumTemperatureLimit", None)
            self._param_floorMinimumTemperatureLimit = data.get("parameters",{}).get("floorMinimumTemperatureLimit", None)
            self._param_floorMaximumTemperatureLimit = data.get("parameters",{}).get("floorMaximumTemperatureLimit", None)
            self._param_externalMinimumTemperatureLimit = data.get("parameters",{}).get("externalMinimumTemperatureLimit", None)
            self._param_externalMaximumTemperatureLimit = data.get("parameters",{}).get("externalMaximumTemperatureLimit", None)
            self._param_internalCalibration = data.get("parameters",{}).get("internalCalibration", None)
            self._param_floorCalibration = data.get("parameters",{}).get("floorCalibration", None)
            self._param_externalCalibration = data.get("parameters",{}).get("externalCalibration", None)
            self._param_regulationMode = data.get("parameters",{}).get("regulationMode", None)
            self._param_temperatureControlHysteresis = data.get("parameters",{}).get("temperatureControlHysteresis", None)
            self._param_temperatureDisplay = data.get("parameters",{}).get("temperatureDisplay", None)
            self._param_activeDisplayBrightness = data.get("parameters",{}).get("activeDisplayBrightness", None)
            self._param_standbyDisplayBrightness = data.get("parameters",{}).get("standbyDisplayBrightness", None)
            self._param_actionAfterError = data.get("parameters",{}).get("actionAfterError", None)
            self._param_powerRegulatorActiveTime = data.get("parameters",{}).get("powerRegulatorActiveTime", None)
            self._param_sizeOfLoad = data.get("parameters",{}).get("sizeOfLoad", None)
            self._param_disableButtons = data.get("parameters",{}).get("disableButtons", None)

            self._owd_openWindowDetection = data.get("parameters",{}).get("OWD",{}).get("openWindowDetection", None)
            self._owd_activeNow = data.get("parameters",{}).get("OWD",{}).get("activeNow", None)    
            self._net_ssid = data.get("network",{}).get("SSID", None)
            self._net_mac = data.get("network",{}).get("mac", None)
            self._net_ipAddress = data.get("network",{}).get("ipAddress", None)
            self._net_wifiSignalStrength = data.get("network",{}).get("wifiSignalStrength", None)
            self._net_status = data.get("network",{}).get("status", None)
            self._hw_firmware = data.get("firmware", None)

            _LOGGER.info("Status fetched from the Heatit WiFi6: %s", self.name)
        else:
            _LOGGER.warning("Status fetch failed from the Heatit WiFi6: %s.", self.name)
            self._available = False
            self._param_operatingMode = None
            self._hvac_mode = HVACMode.OFF      # Set UI disabled/Off, when status can't fetched.
            self._hvac_action = HVACAction.OFF
            self._net_status = "fail"

    @property
    def unique_id(self):
        return f"heatit_wifi6_{self._device_id}"

    @property
    def name(self):
        if self._name:
            return self._name
        else:
            return ""

    @name.setter
    def name(self, name):
        if not name:
            return
        self._name= name

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
        return self._temperature

    @property
    def target_temperature(self):
        match self._param_operatingMode:
            case 1: return self._param_heatingSetpoint
            case 2: return self._param_coolingSetpoint
            case 3: return self._param_ecoSetpoint
            case _: return None

    @property
    def hvac_mode(self):
        return self._hvac_mode
    
    @property
    def hvac_modes(self):
        match self._hvac_mode:
            case HVACMode.HEAT: return [HVACMode.OFF, HVACMode.HEAT]
            case HVACMode.COOL: return [HVACMode.OFF, HVACMode.COOL]
            case _:  # heating mode as default.
                return [HVACMode.OFF, HVACMode.HEAT]

    @property
    def hvac_action(self):
       return self._hvac_action

    @property
    def supported_features(self):
        return ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def extra_state_attributes(self):  # custom properties
       return {
            "info_currentPower": self._info_currentPower,
            "info_totalConsumption": self._info_totalConsumption,
            "info_internalTemperature": self._info_internalTemperature,
            "info_externalTemperature": self._info_externalTemperature,
            "info_floorTemperature": self._info_floorTemperature,

            "param_sensorMode": SENSORMODES.get(self._param_sensorMode, "Unknown"),
            "param_sensorValue": SENSORVALUES.get(self._param_sensorValue, "Unknown"),
            "param_heatingSetpoint": self._param_heatingSetpoint,
            "param_coolingSetpoint": self._param_coolingSetpoint,
            "param_ecoSetpoint": self._param_ecoSetpoint,
            "param_internalMinimumTemperatureLimit": self._param_internalMinimumTemperatureLimit,
            "param_internalMaximumTemperatureLimit": self._param_internalMaximumTemperatureLimit,
            "param_floorMinimumTemperatureLimit": self._param_floorMinimumTemperatureLimit,
            "param_floorMaximumTemperatureLimit": self._param_floorMaximumTemperatureLimit,
            "param_externalMinimumTemperatureLimit": self._param_externalMinimumTemperatureLimit,
            "param_externalMaximumTemperatureLimit": self._param_externalMaximumTemperatureLimit,
            "param_internalCalibration": self._param_internalCalibration,
            "param_floorCalibration": self._param_floorCalibration,
            "param_externalCalibration": self._param_externalCalibration,
            "param_regulationMode": self._param_regulationMode,
            "param_temperatureControlHysteresis": self._param_temperatureControlHysteresis,
            "param_temperatureDisplay": self._param_temperatureDisplay,
            "param_activeDisplayBrightness": self._param_activeDisplayBrightness,
            "param_standbyDisplayBrightness": self._param_standbyDisplayBrightness,
            "param_actionAfterError": self._param_actionAfterError,
            "param_powerRegulatorActiveTime": self._param_powerRegulatorActiveTime,
            "param_sizeOfLoad": self._param_sizeOfLoad,
            "param_disableButtons": self._param_disableButtons,

            "owd_openWindowDetection": self._owd_openWindowDetection,
            "owd_activeNow": self._owd_activeNow,
            "net_ssid": self._net_ssid,
            "net_mac": self._net_mac,
            "net_ipAddress": self._net_ipAddress,
            "net_wifiSignalStrength": self._net_wifiSignalStrength,
            "net_status": self._net_status,
            "hw_firmware": self._hw_firmware           
       }
    
    @property
    def available(self) -> bool:
       """Return True if device is available."""
       return self._available


    async def async_set_temperature(self, **kwargs):
        # If the Heatit device is switched off don't change the target temperatures.
        if self._hvac_mode == HVACMode.OFF:
            _LOGGER.info("async_set_temperature(): The device %s is switched off. Target temperature can changed only when device is on.", self._name)
            await self.async_update()
            self.schedule_update_ha_state()
            self.hass.components.persistent_notification.create("Target temperature can changed only when Heatit WiFi6 device is ON.", title="Heatif WiFi6 Thermostat")
            return
        temperature = kwargs.get("temperature")
        if temperature is None:
            _LOGGER.error("async_set_temperature(): A new target temperature not set/known. Change target value aborted.")
            return
        self._set_temperature_pending = True
        match self._param_operatingMode:
            case 1: param = "heatingSetpoint"
            case 2: param = "coolingSetpoint"
            case 3: param = "ecoSetpoint"
            case _: return
        if await self._api.set_parameter(param, temperature):
            setattr(self, param, temperature)  # set value into coolingSetpoint, ecoSetpoint or heatingSetpoint.
            self._set_temperature_pending = False
            await self.async_update()
        self._set_temperature_pending = False # also here, if set_parameter() fails.

    async def async_set_preset_mode(self, preset_mode):
            _LOGGER.warning("async_set_preset_mode(): Preset modes not implemented. It should be better to change target temperature by automation than use presets on device side. (%s)", str(preset_mode))
            return

    async def async_set_hvac_mode(self, hvac_mode, force=False):
        if not force and hvac_mode not in self.hvac_modes:
            _LOGGER.error("async_set_hvac_mode(): unsupported HVACMode: %s", str(hvac_mode))
            return
        if await self._api.set_parameter("operatingMode", await self._hvac_mode_to_heatit_operatingmode(hvac_mode)):
            await self.async_update()

    async def _hvac_mode_to_heatit_operatingmode(self, mode):
        match mode:
            case HVACMode.OFF:  return 0
            case HVACMode.HEAT: return 1
            case HVACMode.COOL: return 2
            case _:  # Should not happen.
                _LOGGER.error("_hvac_mode_to_heatit_operatingmode(): Unsupported mode requested from Home Assistant to Heatit: %s", str(mode))
                return -1

    # Heatit's operatingMode = HVACMode
    async def _heatit_operatingmode_to_hvac_mode(self, operatingmode):
        match operatingmode:
            case 0: return HVACMode.OFF   # Off.
            case 1: return HVACMode.HEAT  # Heating when needed by heatingSetpoint.
            case 2: return HVACMode.COOL  # Cooling when needed by coolingSetpoint.
            case 3: return HVACMode.HEAT  # 3=Eco. Works like heating. In the Heatit device, Eco should be preset, not operation mode. (!)
            case _:  # Should not happen.
                _LOGGER.error("_heatit_operatingmode_to_hvac_mode(): Unknown state from Heatit: %s", str(operatingmode))
                return None

    # Heatit's state = HVACAction
    async def _heatit_state_to_hvac_action(self, state):
        match state:
            case "Idle": return HVACAction.OFF if self._hvac_mode == HVACMode.OFF else HVACAction.IDLE  # Note: _hvac_mode should be decided before _hvac_action.
            case "Heating": return HVACAction.HEATING  # Heating mode. Power on until temperature increased to the target (heatingSetpoint).
            case "Cooling": return HVACAction.COOLING  # Cooling mode. Power on until temperature decreased to the target (coolingSetpoint).
            case _:  # Should not happen.
                _LOGGER.error("_heatit_state_to_hvac_action(): Unknown operation mode from Heatit: %s", str(state))
                return None
