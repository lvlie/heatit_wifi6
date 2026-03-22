import logging
import asyncio
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_HOST
from .const import DOMAIN, POLL_INTERVAL
from .api import HeatitWiFi6API

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Stagger device connection on startup to avoid all devices connecting at the same time.
    entries = hass.config_entries.async_entries(DOMAIN)
    try:
        index = [e.entry_id for e in entries].index(entry.entry_id)
    except ValueError:
        index = 0  # fallback if not found; should never happen
    wait_seconds = index * 2 + 2  # Always wait at least 2 seconds for the first, 4s for the second, etc.
    if wait_seconds:
        _LOGGER.info("Waiting %s seconds before connecting Heatit device for host: %s", wait_seconds, str(entry.data[CONF_HOST]))
        await asyncio.sleep(wait_seconds)
    _LOGGER.info("Heatit async_setup_entry() called for host: %s", str(entry.data[CONF_HOST]))

    api = HeatitWiFi6API(entry.data[CONF_HOST])

    async def async_update_data():
        try:
            data = await api.get_status()
            if not data:
                raise UpdateFailed("Failed to fetch data from Heatit WiFi6 thermostat")
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(minutes=POLL_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Remove the Heatit device. async_unload_entry() called for host: %s", str(entry.data[CONF_HOST]))
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
