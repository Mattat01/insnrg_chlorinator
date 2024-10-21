import logging
import requests
import aiohttp
import async_timeout
import uuid
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential, # ORP
    UnitOfEnergy,
    UnitOfTemperature,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

async def async_setup_entry(hass, config, async_add_entities) -> None:
    _LOGGER.debug("Setting up sensors in sensor.py")
    coordinator = hass.data[DOMAIN][config.entry_id]["coordinator"]

    sensors = [
        InsnrgpHSensor(coordinator, "Current pH", "currentPh"),
        InsnrgpHSensor(coordinator, "Set Point pH", "setPointPh"),
        InsnrgpHSensor(coordinator, "pH Connected", "pHConnected"),
        InsnrgOrpSensor(coordinator, "Current ORP", "currentORP"),
        InsnrgOrpSensor(coordinator, "Set Point ORP", "setPointORP"),
        InsnrgOrpSensor(coordinator, "ORP Connected", "orpConnected"),
        InsnrgTempSensor(coordinator, "Current Temperature", "temperature")
    ]

    # Access the timer data
    timer_data = coordinator.data.get("timers", [])

    # Dynamically create timer sensors
    for i, timer in enumerate(timer_data):
        timer_number = timer.get("timer_number", i)
        sensors.append(InsnrgTimerStartSensor(coordinator, f"Timer {timer_number} Start", "start_time", i))
        sensors.append(InsnrgTimerStopSensor(coordinator, f"Timer {timer_number} End", "stop_time", i))
        sensors.append(InsnrgTimerChlorinatorSensor(coordinator, f"Timer {timer_number} Operates Chlorinator", "chlorinator", i))
        sensors.append(InsnrgTimerEnabledSensor(coordinator, f"Timer {timer_number} Enabled", "enabled", i))

    async_add_entities(sensors)

    # Store the sensors in hass.data for future updates
    hass.data[DOMAIN][config.entry_id]["sensors"].extend(sensors)


async def update_sensors(hass, sensors):
    for sensor in sensors:
        await sensor.async_update()

class InsnrgpHSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PH
    _attr_suggested_display_precision = 1

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        # Consider sanity check on returned value as ORP could be 650000 if initially updated when the chlorinator is off, maybe? 
        return self._coordinator.data.get("pool_chemistry", {}).get(self._data_key)

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

class InsnrgOrpSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
    _attr_suggested_display_precision = 0

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        # Consider sanity check on returned value as ORP could be 650000 if initially updated when the chlorinator is off, maybe? 
        return self._coordinator.data.get("pool_chemistry", {}).get(self._data_key)

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

class InsnrgTempSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    @property
    def name(self):
        return f"Pool {self._name}"

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

class InsnrgTimerStartSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    @property
    def name(self):
        return f"INSNRG {self._name}"

    @property
    def state(self):
        """Return the start time for this timer."""
        return self._coordinator.data.get("timers", [])[self._timer_index].get(self._data_key) 

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

class InsnrgTimerStopSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    @property
    def name(self):
        return f"INSNRG {self._name}"

    @property
    def state(self):
        """Return the start time for this timer."""
        return self._coordinator.data.get("timers", [])[self._timer_index].get(self._data_key) 

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

class InsnrgTimerChlorinatorSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    @property
    def name(self):
        return f"INSNRG {self._name}"

    @property
    def state(self):
        """Return the start time for this timer."""
        return self._coordinator.data.get("timers", [])[self._timer_index].get(self._data_key) 

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

class InsnrgTimerEnabledSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    @property
    def name(self):
        return f"INSNRG {self._name}"

    @property
    def state(self):
        """Return the start time for this timer."""
        return self._coordinator.data.get("timers", [])[self._timer_index].get(self._data_key) 

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

