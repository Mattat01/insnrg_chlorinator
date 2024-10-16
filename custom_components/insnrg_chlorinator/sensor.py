import logging
import requests
import aiohttp
import async_timeout
import uuid
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, API_URL

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(hass, config, async_add_entities) -> None:
    _LOGGER.info("Setting up sensors in sensor.py")
    config_data = hass.config_entries.async_entries(DOMAIN)[0].data
    token = config_data["access_token"]
    system_id = config_data["system_id"]
    coordinator = hass.data[DOMAIN][config.entry_id]["coordinator"]
    _LOGGER.info("checking the coordinator is available: %s", coordinator)

    sensors = [
        InsnrgChlorinatorSensor(coordinator, "Current pH", token, system_id, API_URL, "currentPh"),
        InsnrgChlorinatorSensor(coordinator, "Set Point pH", token, system_id, API_URL, "setPointPh"),
        InsnrgChlorinatorSensor(coordinator, "Current ORP", token, system_id, API_URL, "currentORP"),
        InsnrgChlorinatorSensor(coordinator, "Set Point ORP", token, system_id, API_URL, "setPointORP"),
        InsnrgChlorinatorSensor(coordinator, "pH Connected", token, system_id, API_URL, "pHConnected"),
        InsnrgChlorinatorSensor(coordinator, "ORP Connected", token, system_id, API_URL, "orpConnected")
    ]
    async_add_entities(sensors)
    # Store the sensors in hass.data for future updates
    hass.data[DOMAIN][config.entry_id]["sensors"].extend(sensors)


async def update_sensors(hass, sensors):
    for sensor in sensors:
        await sensor.async_update()

class InsnrgChlorinatorSensor(SensorEntity):
    def __init__(self, coordinator, name, token, system_id, api_url, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._token = token
        self._system_id = system_id
        self._api_url = api_url
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{system_id}_{data_key}"))

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        return self._coordinator.data.get(self._data_key)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._coordinator.updated
        }

    @property
    def unique_id(self):
        return self._unique_id

    async def async_update(self):
        """Request an update from the coordinator."""
        await self._coordinator.async_request_refresh()

 