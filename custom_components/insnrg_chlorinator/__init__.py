import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType


_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the INSNRG Chlorinator component."""
    _LOGGER.info("Setting up INSNRG Chlorinator")
    # Perform any global setup here, if needed.
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up INSNRG Chlorinator from a config entry."""
    # This is where you will set up the sensors and other parts of the integration
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up sensors
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
