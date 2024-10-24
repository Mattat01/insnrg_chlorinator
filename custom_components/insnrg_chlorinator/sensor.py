import logging
import requests
import aiohttp
import async_timeout
import uuid
from datetime import datetime, timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import StateType
from homeassistant.core import callback
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    RestoreEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricPotential, # ORP
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
        InsnrgConnectionSensor(coordinator, "pH Connected", "pHConnected"),
        InsnrgOrpSensor(coordinator, "Current ORP", "currentORP"),
        InsnrgOrpSensor(coordinator, "Set Point ORP", "setPointORP"),
        InsnrgConnectionSensor(coordinator, "ORP Connected", "orpConnected"),
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

class InsnrgConnectionSensor(RestoreEntity):
    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._last_state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._last_state = await self.async_get_last_state()
        if not self._last_state:
            _LOGGER.info(f"This is the first time {self._name} has been added to HA. It won't obtain data until after your chlorinator is running for an hour.")
            return
        _LOGGER.info(f"Recovering last known state of {self._name} ({self._last_state.state}).")
        self._state = self._last_state.state

        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        # Check if pool_chemistry is not None before updating the state
        try:
            pool_chemistry = self._coordinator.data.get("pool_chemistry")
        except Exception:
            pool_chemistry = None
        if pool_chemistry is None:
            # If pool_chemistry is None (chlorinator off), don't update the state
            return self._last_state.state  # Return the last known state or None if the entity has not existed before
        # Update the state based on the pool_chemistry data
        self._state = pool_chemistry.get(self._data_key)
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._coordinator.updated
        }

    @property
    def unique_id(self):
        return self._unique_id

class InsnrgpHSensor(RestoreEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.PH
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._last_state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._last_state = await self.async_get_last_state()
        if not self._last_state:
            _LOGGER.info(f"This is the first time {self._name} has been added to HA. It won't obtain data until after your chlorinator is running for an hour.")
            return
        _LOGGER.info(f"Recovering last known state of {self._name} ({self._last_state.state}).")
        self._state = self._last_state.state

        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        # Check if pool_chemistry is not None before updating the state
        try:
            pool_chemistry = self._coordinator.data.get("pool_chemistry")
        except Exception:
            pool_chemistry = None
        if pool_chemistry is None:
            # If pool_chemistry is None (chlorinator off), return nothing so the state is not updated
            return self._last_state.state
        if pool_chemistry.get(self._data_key) > 14:
            return self._last_state.state # if the value is crazy out of range, don't update the state
        # Update the state based on the pool_chemistry data
        self._state = pool_chemistry.get(self._data_key)
        return self._state

    @property
    def native_value(self) -> StateType:
        """Return value of sensor."""
        return self.attribute_value

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._coordinator.updated
        }

    @property
    def unique_id(self):
        return self._unique_id

class InsnrgOrpSensor(RestoreEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, name, data_key):
        self._coordinator = coordinator
        self._name = name
        self._state = None
        self._last_state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._last_state = await self.async_get_last_state()
        if not self._last_state:
            _LOGGER.info(f"This is the first time {self._name} has been added to HA. It won't obtain data until after your chlorinator is running for an hour.")
            return
        _LOGGER.info(f"Recovering last known state of {self._name} ({self._last_state.state}).")
        self._state = self._last_state.state

        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

    @property
    def name(self):
        return f"Chlorinator {self._name}"

    @property
    def state(self):
        # Check if pool_chemistry is not None before updating the state
        try:
            pool_chemistry = self._coordinator.data.get("pool_chemistry")
        except Exception:
            pool_chemistry = None
        if pool_chemistry is None:
            # If pool_chemistry is None (chlorinator off), return nothing so the state is not updated
            return self._last_state.state
        if pool_chemistry.get(self._data_key) > 2000:
            return self._last_state.state # if the value is crazy out of range, don't update the state
        # Update the state based on the pool_chemistry data
        self._state = pool_chemistry.get(self._data_key)
        return self._state

    @property
    def native_value(self) -> StateType:
        """Return value of sensor."""
        return self.attribute_value

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._coordinator.updated,
            "state_class": "measurement",
            "unit_of_measurement": "mV"
        }

    @property
    def unique_id(self):
        return self._unique_id

### We don't need to get the last known state for the following sensors as we take whatever the API provides even if the chlorinator is not running. 
### For the chemistry page we retun none instead of the result from the API outside chlorination hours because sometimes the data is wrong then, so we just use the last known value.

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

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

    @property
    def name(self):
        return f"Pool {self._name}"

    @property
    def state(self):
        return self._coordinator.data.get(self._data_key)

    @property
    def native_value(self) -> StateType:
        """Return value of sensor."""
        return self.attribute_value

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "last_updated": self._coordinator.updated
        }

    @property
    def unique_id(self):
        return self._unique_id

class InsnrgTimerStartSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

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

class InsnrgTimerStopSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

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

class InsnrgTimerChlorinatorSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

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

class InsnrgTimerEnabledSensor(SensorEntity):
    def __init__(self, coordinator, name, data_key, timer_index):
        self._coordinator = coordinator
        self._name = name
        self._timer_index = timer_index
        self._state = None
        self._data_key = data_key
        self._last_updated = None
        self._unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{DOMAIN}_{data_key}_{timer_index}"))

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Register the callback to update sensor when coordinator updates
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug(f"Updating {self._name} via callback.")
        # Notify Home Assistant that the sensor's state has been updated
        self.async_write_ha_state()

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

