import logging
import requests
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import datetime, timedelta
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
)
from homeassistant.const import (
    Platform,
)
from .const import DOMAIN, API_URL

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

class InsnrgChlorinatorCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates."""
    _LOGGER.info("Setting up INSNRG Coordinator")

    def __init__(self, hass: HomeAssistant, api_url, system_id, token, refresh_token, id_token):
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name = DOMAIN, update_interval = SCAN_INTERVAL)
        self.api_url = api_url
        self.system_id = system_id
        self.token = token
        self.refresh_token = refresh_token
        self.id_token = id_token
        self.updated = datetime.now().isoformat()

    async def _async_update_data(self):
        """Fetch data from the API and return it."""
        # Check if token has expired, if so, refresh it
        if self._token_expired():
            await self._refresh_token()

        headers = {"Authorization": f"Bearer {self.token}"}
        body = {
            "systemId": self.system_id,
            "params": "ChemistryScreen",
            "action": "view"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    async with session.post(self.api_url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.updated = datetime.now().isoformat()
                            _LOGGER.info("updating chlorinator")
                            return data.get("poolChemistry", {})
                        else:
                            _LOGGER.error("Error fetching data from API: %s", await response.text())
                            raise UpdateFailed(f"Error {response.status} from API")
            except Exception as err:
                _LOGGER.error(f"Exception during chlorinator sensor update: {err}")
                raise UpdateFailed(f"Update error: {err}")

    def _token_expired(self):
        """Check if the token has expired. You need to track token expiry time."""
        # You will need logic here to track when the token expires and check it
        # Typically, a JWT (access token) has an "exp" claim you can check
        # This is a placeholder for the actual expiration check
        return False

    async def _refresh_token(self):
        """Use the refresh token to get a new access token."""
        _LOGGER.info("Refreshing access token")

        # Create the request body for token refresh
        refresh_url = f"https://cognito-idp.us-east-2.amazonaws.com"
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        }
        payload = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": "50kmkes69ij352vpq3ec7dfki2",
            "AuthParameters": {
                "REFRESH_TOKEN": self.refresh_token
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(refresh_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data["AuthenticationResult"]["AccessToken"]
                    _LOGGER.info("Access token refreshed successfully")
                elif response.status_code == 400 or response.status_code == 401:
                    # Token refresh failed, likely due to expired or invalid refresh token
                    _LOGGER.error("Refresh token expired, prompting user for reauthentication.")
                    # Here you could trigger a reauthentication process or raise an error
                else:
                    _LOGGER.error("Failed to refresh access token")
                    raise UpdateFailed(f"Error {response.status} refreshing token")

async def async_setup(hass: HomeAssistant, config: ConfigType | None) -> bool:
    """Set up the INSNRG Chlorinator component."""
    _LOGGER.info("Setting up INSNRG Chlorinator")
    # Perform any global setup here, if needed.
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up INSNRG Chlorinator from a config entry."""
    _LOGGER.info("Setting up entry for INSNRG Chlorinator with entry_id: %s", config_entry.entry_id)

    # Extract tokens from config_entry
    access_token = config_entry.data.get("access_token")
    refresh_token = config_entry.data.get("refresh_token")
    id_token = config_entry.data.get("id_token")

    # Set up your coordinator
    coordinator = InsnrgChlorinatorCoordinator(
        hass,
        api_url=API_URL,
        system_id=config_entry.data["system_id"],
        token=access_token,
        refresh_token=refresh_token,
        id_token=id_token,  # In case it's needed later
    )
    _LOGGER.info("Coordinator: %s", coordinator)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][config_entry.entry_id] = {
        "data": config_entry.data,
        "coordinator": coordinator,
        "sensors": []
    }

    # Set up sensors
    _LOGGER.info("Creating tasks for sensor setup")
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Verify that sensors are set up correctly by adding a check after forward_entry_setups
    sensors = hass.data[DOMAIN][config_entry.entry_id]["sensors"]
    if not sensors:
        _LOGGER.warning("No sensors were set up for entry ID: %s", config_entry.entry_id)
    else:
        # Log each sensor's name and current state
        sensor_info = ", ".join([f"{sensor.name} (state: {sensor.state})" for sensor in sensors])
        _LOGGER.info("Sensors set up for entry ID %s: %s", config_entry.entry_id, sensor_info)

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
    return unload_ok

async def update_sensors_service(hass: HomeAssistant, call: ServiceCall):
    """Service to manually trigger a sensor update."""
    entry_id = call.data.get("entry_id")
    config_entry = hass.config_entries.async_get_entry(entry_id)
    
    if config_entry is None:
        _LOGGER.error("Entry ID not found: %s", entry_id)
        return

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    await coordinator.async_request_refresh()
