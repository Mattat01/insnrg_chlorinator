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

async def async_setup_entry(hass, config, async_add_entities) -> None:
    _LOGGER.info("Setting up sensors in sensor.py")
    config_data = hass.config_entries.async_entries(DOMAIN)[0].data
    token = config_data["bearer_token"]
    system_id = config_data["system_id"]

    sensors = [
        InsnrgChlorinatorSensor("Current pH", token, system_id, API_URL, "currentPh"),
        InsnrgChlorinatorSensor("Set Point pH", token, system_id, API_URL, "setPointPh"),
        InsnrgChlorinatorSensor("Current ORP", token, system_id, API_URL, "currentORP"),
        InsnrgChlorinatorSensor("Set Point ORP", token, system_id, API_URL, "setPointORP"),
        InsnrgChlorinatorSensor("pH Connected", token, system_id, API_URL, "pHConnected"),
        InsnrgChlorinatorSensor("ORP Connected", token, system_id, API_URL, "orpConnected")
    ]
    async_add_entities(sensors)
    # Store the sensors in hass.data for future updates
    hass.data[DOMAIN][config.entry_id]["sensors"].extend(sensors)

    # Schedule updates once a day
    async_track_time_interval(hass, lambda _: update_sensors(hass, sensors), timedelta(days=1))

async def update_sensors(hass, sensors):
    for sensor in sensors:
        await sensor.async_update()

class InsnrgChlorinatorSensor(SensorEntity):
    def __init__(self, name, token, system_id, api_url, data_key):
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
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._last_updated
        }

    @property
    def unique_id(self):
        return self._unique_id

    async def async_update(self):
        headers = {"Authorization": f"Bearer {self._token}"}
        body = {
            "systemId": self._system_id,
            "params": "ChemistryScreen",
            "action": "view"
        }

        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):  # Set a timeout for the request
                async with session.post(self._api_url, headers=headers, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        pool_data = data.get("poolChemistry", {})
                        self._state = pool_data.get(self._data_key)
                        self._last_updated = datetime.now().isoformat()
                    else:
                        _LOGGER.error(f"Failed to update {self._name}: {await response.text()}")
