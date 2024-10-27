import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
)
from homeassistant.const import (
    Platform,
)
from .const import DOMAIN, API_URL
from .coordinator import InsnrgChlorinatorCoordinator  # Import the new coordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType | None) -> bool:
    """Set up the INSNRG Chlorinator component."""
    #_LOGGER.debug("Setting up INSNRG Chlorinator")
    # Perform any global setup here, if needed.
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up INSNRG Chlorinator from a config entry."""
    _LOGGER.debug("Setting up entry for INSNRG Chlorinator with entry_id: %s", config_entry.entry_id)

    # Extract tokens from config_entry
    access_token = config_entry.data.get("access_token")
    expiry = config_entry.data.get("expiry")
    refresh_token = config_entry.data.get("refresh_token")
    id_token = config_entry.data.get("id_token")
    system_id = config_entry.data.get("system_id")

    # Set up the coordinator
    coordinator = InsnrgChlorinatorCoordinator(
        hass,
        api_url=API_URL,
        system_id=system_id,
        token=access_token,
        expiry=expiry,
        refresh_token=refresh_token,
        id_token=id_token,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("First refresh complete")

    hass.data[DOMAIN][config_entry.entry_id] = {
        "data": config_entry.data,
        "coordinator": coordinator,
        "sensors": []
    }

    # Set up sensors
    _LOGGER.debug("Creating tasks for sensor setup")
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Verify that sensors are set up correctly by adding a check after forward_entry_setups
    sensors = hass.data[DOMAIN][config_entry.entry_id]["sensors"]
    if not sensors:
        _LOGGER.warning("No sensors were set up for entry ID: %s", config_entry.entry_id)
    else:
        # Log each sensor's name and current state
        sensor_info = ", ".join([f"{sensor.name} (state: {sensor.state})" for sensor in sensors])
        _LOGGER.debug("Sensors set up for entry ID %s: %s", config_entry.entry_id, sensor_info)

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
    return unload_ok
