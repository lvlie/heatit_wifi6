"""Sensor platform for the Heatit WiFi6 thermostat."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Heatit WiFi6 sensors from a config entry."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data["coordinator"]
    device_id = domain_data["device_id"]
    name = entry.data[CONF_NAME]

    async_add_entities(
        [
            HeatitWiFi6TemperatureSensor(coordinator, name, device_id),
            HeatitWiFi6TargetTemperatureSensor(coordinator, name, device_id),
            HeatitWiFi6PowerSensor(coordinator, name, device_id),
            HeatitWiFi6EnergySensor(coordinator, name, device_id),
        ]
    )


class HeatitWiFi6SensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Heatit WiFi6 sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        name: str,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_name = name
        self._device_id = device_id

    @property
    def available(self) -> bool:
        """Return True if the coordinator was able to fetch data."""
        return self.coordinator.last_update_success

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


class HeatitWiFi6TemperatureSensor(HeatitWiFi6SensorBase):
    """Current temperature, selected by the configured sensor mode."""

    _attr_translation_key = "current_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        name: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_current_temperature"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        sensor_mode = data.get("parameters", {}).get("sensorMode")
        if sensor_mode == 0:
            return data.get("floorTemperature")
        if sensor_mode in (3, 4):
            return data.get("externalTemperature")
        return data.get("internalTemperature")


class HeatitWiFi6TargetTemperatureSensor(HeatitWiFi6SensorBase):
    """Target temperature based on the active operating mode."""

    _attr_translation_key = "target_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        name: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_target_temperature"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        params = data.get("parameters", {})
        operating_mode = params.get("operatingMode")
        if operating_mode == 1:
            return params.get("heatingSetpoint")
        if operating_mode == 2:
            return params.get("coolingSetpoint")
        if operating_mode == 3:
            return params.get("ecoSetpoint")
        return None


class HeatitWiFi6PowerSensor(HeatitWiFi6SensorBase):
    """Instantaneous power consumption sensor."""

    _attr_translation_key = "power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        name: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_power"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("currentPower")


class HeatitWiFi6EnergySensor(HeatitWiFi6SensorBase):
    """Cumulative energy consumption sensor."""

    _attr_translation_key = "energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        name: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, name, device_id)
        self._attr_unique_id = f"heatit_wifi6_{device_id}_energy"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        return data.get("totalConsumption")
