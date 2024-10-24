import logging
import aiohttp
import async_timeout
import aioboto3
import json
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from .const import DOMAIN, ClientId

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
        self.last_pool_chemistry = None
        self.updated = datetime.now().isoformat()

    async def _async_update_data(self):
        """Fetch data from the API and return it."""
        # Check if token has expired, if so, refresh it
        if self._token_expired():
            await self._refresh_token()

        pool_chemistry = None
        # Step 1: Update timers
        _LOGGER.debug("Updating timers.")
        timers = await self._get_timers()
    
        if timers:
            # Step 2: Check for active timers where chlorinator == True
            current_time = datetime.now().strftime("%H:%M")
            active_timer_found = False
    
            for timer in timers:
                start_time = timer.get("start_time")
                stop_time = timer.get("stop_time")
                chlorinator = timer.get("chlorinator", 0)
                enabled = timer.get("enabled", 0)
                if enabled and chlorinator and start_time <= current_time <= stop_time:
                    _LOGGER.debug(f"Active timer found: Timer {timer['timer_number']} from {start_time} to {stop_time}.")
                    active_timer_found = True
                    break

        pool_chemistry = await self._get_chemistry()

        # Step 4: Update temperature
        _LOGGER.debug("Updating pool temperature.")
        temperature = await self._get_temp()
        if not temperature:
            _LOGGER.info("Failed to retrieve temperature data or your reading is 0 degrees.") 
        else:
            _LOGGER.debug("Retrieved Temp: %s", temperature)

        # Bundle and return all data: timers, temperature, and pool chemistry
        if active_timer_found:
            _LOGGER.info("The chlorinator is on. Using current chemistry.")
            self.last_pool_chemistry = pool_chemistry
            return {
                "timers": timers,
                "temperature": temperature,
                "pool_chemistry": pool_chemistry
            }
        elif self.last_pool_chemistry:
            _LOGGER.warning("Using last known pool_chemistry, as the chlorinator is off and current readings may be inaccurate.")
            return {
                "timers": timers,
                "temperature": temperature,
                "pool_chemistry": self.last_pool_chemistry
            }
        else:
            _LOGGER.warning("Not updating pool_chemistry, as the chlorinator is off and may be inaccurate. No previous data available")
            return {
                "timers": timers,
                "temperature": temperature,
                "pool_chemistry": None
            }

    def _token_expired(self):
        """Check if the token has expired."""

        # If expiry is a string, convert it to a datetime object
        if isinstance(self.expiry, str):
            try:
                expiry_datetime = datetime.strptime(self.expiry, "%Y-%m-%dT%H:%M:%S.%f")
                _LOGGER.debug("Converted expiry from string to datetime: %s", expiry_datetime)
            except ValueError as e:
                _LOGGER.error(f"Failed to convert expiry string to datetime: {e}")
                return True  # Handle error by treating token as expired
        else:
            expiry_datetime = self.expiry

        if expiry_datetime < datetime.now():
            _LOGGER.debug("Token has expired")
            return True
        else:
            _LOGGER.debug("Token is alive")
            return False


    async def _refresh_token(self):
        """Use the refresh token to get a new access token."""
        _LOGGER.debug("Refreshing access token")

        session = aioboto3.Session()

        try:
            async with session.client('cognito-idp', region_name='us-east-2') as client:
                response = await client.initiate_auth(
                    ClientId=ClientId,
                    AuthFlow='REFRESH_TOKEN_AUTH',
                    AuthParameters={
                        'REFRESH_TOKEN': self.refresh_token
                    }
                )

                #_LOGGER.debug("Token refresh response received: %s", response)

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
#       Consider failure messages and handle to prompt credential check instead of UpdateFailed.
#                raise ConfigEntryAuthFailed("Could not log in, please check your email and password.") from e
                raise UpdateFailed("Refresh token invalid or expired. Reauthentication required.")
            else:
                _LOGGER.error(f"ClientError during token refresh: {e}")
                raise UpdateFailed(f"Error refreshing token: {e}")
    
        except Exception as e:
            _LOGGER.error(f"Unexpected error during token refresh: {e}")
            raise UpdateFailed(f"Unexpected error refreshing token: {e}")

    async def _get_timers(self):
        
        headers = {
            "Authorization": f"Bearer {self.id_token}",
        }
        body = {
            "systemId": self.system_id,
            "params": "SetTimerAppliance",
            "action": "view"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    async with session.post(self.api_url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Extract timers
                            timers = data.get("timers", [])
                            if not timers:
                                _LOGGER.warning("No timers found")
                                return None

                            timer_data = []
                            for timer in timers:
                                timer_number = timer.get("timerNumber", None)
                                start_time = timer.get("start", None)
                                stop_time = timer.get("stop", None)
                                chlorinator = timer.get("chlorinator", None)
                                enabled = timer.get("enable", None)

                                timer_info = {
                                    "timer_number": timer_number,
                                    "start_time": start_time,
                                    "stop_time": stop_time,
                                    "chlorinator": chlorinator == 1,
                                    "enabled": enabled == 1
                                }
                                timer_data.append(timer_info)

                                _LOGGER.debug(f"Timer {timer_number} - Start: {start_time}, Stop: {stop_time}, Chlorinator: {chlorinator}, Enabled: {enabled}")

                            return timer_data
                        else:
                            _LOGGER.error(f"Error fetching timers from API: {await response.text()}")
                            raise UpdateFailed(f"Error {response.status} from API")
            except Exception as err:
                _LOGGER.error(f"Exception during timers update: {err}")
                raise UpdateFailed(f"Update error: {err}")

    async def _get_temp(self):
        
        headers = {
            "Authorization": f"Bearer {self.id_token}",
        }
        body = {
            "systemId": self.system_id,
            "params": "DashboardScreen",
            "action": "view"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    async with session.post(self.api_url, headers=headers, json=body) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Extract temp from liveData in system
                            system_data = data.get("system", {})
                            live_data = system_data.get("liveData", "{}")
                            live_data_json = json.loads(live_data)
                            temp = live_data_json.get("temp", None)

                            if temp is not None:
                                _LOGGER.debug(f"Temperature from system liveData: {temp}")
                                return temp
                            else:
                                _LOGGER.warning("Temperature not found in liveData")
                                return 0
                        else:
                            _LOGGER.error(f"Error fetching temperature from API: {await response.text()}")
                            raise UpdateFailed(f"Error {response.status} from API")
            except Exception as err:
                _LOGGER.error(f"Exception during temperature update: {err}")
                raise UpdateFailed(f"Update error: {err}")

    async def _get_chemistry(self):
        
        headers = {
            "Authorization": f"Bearer {self.id_token}",
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
                            _LOGGER.debug("Chemistry data gathered")
                            return data.get("poolChemistry", {})
                        else:
                            _LOGGER.error("Error fetching data from API: %s", await response.text())
                            raise UpdateFailed(f"Error {response.status} from API")
#            # Ideally, raise the ConfigEntryAuthFailed exception, possibly as below
#            except ClientError as e:
#                raise ConfigEntryAuthFailed("Could not log in, please check your email and password.") from e
            except Exception as err:
                _LOGGER.error(f"Exception during chlorinator sensor update: {err}")
                raise UpdateFailed(f"Update error: {err}")
