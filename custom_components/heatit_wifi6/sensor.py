import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfEnergy,
    CONF_HOST,
    CONF_NAME,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .exceptions import CannotConnect

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.debug("async_setup_entry(): Heatit WiFi6 Sensors")

    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]

    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data["coordinator"]
    device_id = domain_data["device_id"]

    entities = [
        HeatitWiFi6TemperatureSensor(coordinator, name, device_id),
        HeatitWiFi6TargetTemperatureSensor(coordinator, name, device_id),
        HeatitWiFi6PowerSensor(coordinator, name, device_id),
        HeatitWiFi6EnergySensor(coordinator, name, device_id),
    ]

    async_add_entities(entities, True)
    return True

class HeatitWiFi6SensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Heatit WiFi6 sensors."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator)
        self._name = name
        self._device_id = device_id

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

class HeatitWiFi6TemperatureSensor(HeatitWiFi6SensorBase):
    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_current_temperature"
        self._attr_name = "Current Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        sensor_mode = data.get("parameters", {}).get("sensorMode", None)
        match sensor_mode:
            case 0: return data.get("floorTemperature", None)
            case 3 | 4: return data.get("externalTemperature", None)
            case _: return data.get("internalTemperature", None)

class HeatitWiFi6TargetTemperatureSensor(HeatitWiFi6SensorBase):
    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_target_temperature"
        self._attr_name = "Target Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        operating_mode = data.get("parameters", {}).get("operatingMode")
        match operating_mode:
            case 1: return data.get("parameters", {}).get("heatingSetpoint", None)
            case 2: return data.get("parameters", {}).get("coolingSetpoint", None)
            case 3: return data.get("parameters", {}).get("ecoSetpoint", None)
            case _: return None

class HeatitWiFi6PowerSensor(HeatitWiFi6SensorBase):
    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_power"
        self._attr_name = "Power"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        return data.get("currentPower", None)

class HeatitWiFi6EnergySensor(HeatitWiFi6SensorBase):
    def __init__(self, coordinator, name, device_id):
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_energy"
        self._attr_name = "Energy"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        return data.get("totalConsumption", None)
