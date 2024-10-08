import logging
from homeassistant.helpers import discovery
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    _LOGGER.info("Setting up INSNRG Chlorinator")
    hass.async_create_task(discovery.async_load_platform(hass, 'sensor', DOMAIN, {}, config))
    return True