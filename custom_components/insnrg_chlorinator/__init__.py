import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
)
from homeassistant.const import (
    Platform,
)
PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType | None) -> bool:
    """Set up the INSNRG Chlorinator component."""
    _LOGGER.info("Setting up INSNRG Chlorinator")
    # Perform any global setup here, if needed.
    hass.data.setdefault(DOMAIN, {})
    # Register the manual update service
    hass.services.async_register(DOMAIN, "update_sensors", update_sensors_service)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up INSNRG Chlorinator from a config entry."""
    _LOGGER.info("Setting up entry for INSNRG Chlorinator with entry_id: %s", entry.entry_id)
    hass.data[DOMAIN][entry.entry_id] = {"data": entry.data, "sensors": []}

    # Set up sensors
    _LOGGER.info("Creating tasks for sensor setup")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Verify that sensors are set up correctly by adding a check after forward_entry_setups
    sensors = hass.data[DOMAIN][entry.entry_id]["sensors"]
    if not sensors:
        _LOGGER.warning("No sensors were set up for entry ID: %s", entry.entry_id)
    else:
        # Log each sensor's name and current state
        sensor_info = ", ".join([f"{sensor.name} (state: {sensor.state})" for sensor in sensors])
        _LOGGER.info("Sensors set up for entry ID %s: %s", entry.entry_id, sensor_info)

    # Schedule daily updates
    async_track_time_interval(hass, lambda now: update_sensors(hass, entry), timedelta(days=1))

    # Initial update
    await update_sensors(hass, entry)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True

async def update_sensors(hass: HomeAssistant, entry: ConfigEntry):
    """Update sensor states by fetching the latest data from the API."""
    # Fetch and update all sensors associated with the entry
    sensors = hass.data[DOMAIN][entry.entry_id].get("sensors", [])
    
    if not sensors:
        _LOGGER.warning("No sensors found for entry ID: %s", entry.entry_id)
        return

    for sensor in sensors:
        await sensor.async_update()
        sensor_info = ", ".join([f"{sensor.name} (state: {sensor.state}, UUID: {sensor.unique_id})"])
        _LOGGER.info("Sensor updated: %s", sensor_info)

async def update_sensors_service(hass: HomeAssistant, call: ServiceCall):
    """Service to manually trigger a sensor update."""
    entry_id = call.data.get("entry_id")  # This would require you to pass the entry ID
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        _LOGGER.error("Entry ID not found: %s", entry_id)
        return
    await update_sensors(hass, entry)
