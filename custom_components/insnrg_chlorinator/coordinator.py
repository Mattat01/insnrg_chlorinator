import logging
import aiohttp
import async_timeout
import aioboto3
from botocore.exceptions import ClientError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import datetime, timedelta
from homeassistant.core import (
    HomeAssistant,
)
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
        self.updated = datetime.now().isoformat()

    async def _async_update_data(self):
        """Fetch data from the API and return it."""
        # Check if token has expired, if so, refresh it
        if self._token_expired():
            _LOGGER.debug("Refreshing Access Token")
            await self._refresh_token()

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
                            _LOGGER.debug("Updating chemistry")
                            return data.get("poolChemistry", {})
                        else:
                            _LOGGER.error("Error fetching data from API: %s", await response.text())
                            raise UpdateFailed(f"Error {response.status} from API")
            except Exception as err:
                _LOGGER.error(f"Exception during chlorinator sensor update: {err}")
                raise UpdateFailed(f"Update error: {err}")

    def _token_expired(self):
        """Check if the token has expired."""
        expiry_datetime = datetime.strptime(self.expiry, "%Y-%m-%dT%H:%M:%S.%f")
        _LOGGER.debug(expiry_datetime)
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
                # Here, you can trigger a reauthentication process or return an error
                raise UpdateFailed("Refresh token invalid or expired. Reauthentication required.")
            else:
                _LOGGER.error(f"ClientError during token refresh: {e}")
                raise UpdateFailed(f"Error refreshing token: {e}")
    
        except Exception as e:
            _LOGGER.error(f"Unexpected error during token refresh: {e}")
            raise UpdateFailed(f"Unexpected error refreshing token: {e}")
