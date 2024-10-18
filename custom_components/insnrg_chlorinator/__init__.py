import logging
import requests
import aiohttp
import async_timeout
import aioboto3
from pycognito import AWSSRP
from botocore.exceptions import ClientError
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
from .const import DOMAIN, API_URL, ClientId

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=1)

class InsnrgChlorinatorCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates."""
    _LOGGER.debug("Setting up INSNRG Coordinator")

    def __init__(self, hass: HomeAssistant, api_url, system_id, token, expiry, refresh_token, id_token):
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name = DOMAIN, update_interval = SCAN_INTERVAL)
        self.api_url = api_url
        self.system_id = system_id
        self.token = token
        self.expiry = expiry
        self.refresh_token = refresh_token
        self.id_token = id_token
        self.updated = datetime.now().isoformat()

    async def _async_update_data(self):
        """Fetch data from the API and return it."""
        # Check if token has expired, if so, refresh it
        if self._token_expired():
            _LOGGER.debug("Refreshing Access Token")
            await self._refresh_token()

        _LOGGER.debug("Access Token: %s", self.token)
        _LOGGER.debug("ID Token: %s", self.id_token)
        _LOGGER.debug("System ID: %s", self.system_id)
        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Origin": "https://www.insnrgapp.com"
        }
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
                            _LOGGER.debug("updating chlorinator")
                            return data.get("poolChemistry", {})
                        else:
                            _LOGGER.error("Error fetching data from API: %s", await response.text())
                            raise UpdateFailed(f"Error {response.status} from API")
            except Exception as err:
                _LOGGER.error(f"Exception during chlorinator sensor update: {err}")
                raise UpdateFailed(f"Update error: {err}")

    def _token_expired(self):
        """Check if the token has expired."""
        _LOGGER.debug("Testing to determine if Token has expired.")
        return self.expiry < datetime.now()

    async def _refresh_token(self):
        """Use the refresh token to get a new access token."""
        _LOGGER.debug("Refreshing access token")

        session = aioboto3.Session()

        try:
            async with session.client('cognito-idp', region_name='us-east-2') as client:
                _LOGGER.debug("Starting token refresh using REFRESH_TOKEN_AUTH")

                # Make the token refresh request
                response = await client.initiate_auth(
                    ClientId=ClientId,
                    AuthFlow='REFRESH_TOKEN_AUTH',
                    AuthParameters={
                        'REFRESH_TOKEN': self.refresh_token
                    }
                )

                _LOGGER.debug("Token refresh response received: %s", response)

                # Extract new tokens from the response
                auth_result = response['AuthenticationResult']
                self.token = auth_result['AccessToken']
                self.expiry = timedelta(seconds=auth_result['ExpiresIn']) + datetime.now()
                self.id_token = auth_result['IdToken']

                # Refresh token remains the same, unless provided
                if 'RefreshToken' in auth_result:
                    self.refresh_token = auth_result['RefreshToken']

                _LOGGER.debug("Token refresh successful: New access token and expiry retrieved")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ('NotAuthorizedException', 'InvalidRefreshTokenException'):
                _LOGGER.error("Refresh token expired or invalid, prompting user for reauthentication.")
                # Here, you can trigger a reauthentication process or return an error
                raise UpdateFailed("Refresh token invalid or expired. Reauthentication required.")
            else:
                _LOGGER.error(f"ClientError during token refresh: {e}")
                raise UpdateFailed(f"Error refreshing token: {e}")
    
        except Exception as e:
            _LOGGER.error(f"Unexpected error during token refresh: {e}")
            raise UpdateFailed(f"Unexpected error refreshing token: {e}")

async def async_setup(hass: HomeAssistant, config: ConfigType | None) -> bool:
    """Set up the INSNRG Chlorinator component."""
    _LOGGER.debug("Setting up INSNRG Chlorinator")
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

    # Set up your coordinator
    coordinator = InsnrgChlorinatorCoordinator(
        hass,
        api_url=API_URL,
        system_id=config_entry.data["system_id"],
        token=access_token,
        expiry=expiry,
        refresh_token=refresh_token,
        id_token=id_token,  # In case it's needed later
    )
    _LOGGER.debug("Coordinator: %s", coordinator)

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

async def update_sensors_service(hass: HomeAssistant, call: ServiceCall):
    """Service to manually trigger a sensor update."""
    entry_id = call.data.get("entry_id")
    config_entry = hass.config_entries.async_get_entry(entry_id)
    
    if config_entry is None:
        _LOGGER.error("Entry ID not found: %s", entry_id)
        return

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    await coordinator.async_request_refresh()
