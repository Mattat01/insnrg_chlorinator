import voluptuous as vol
import logging
import aiohttp
import async_timeout
from datetime import datetime, timedelta
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, ClientId, PoolId, API_SystemID_URL
import aioboto3
from pycognito import AWSSRP
from botocore.exceptions import ClientError

_LOGGER = logging.getLogger(__name__)

@callback
def configured_instances(hass):
    return {entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)}

class InsnrgChlorinatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Log input for debugging
            _LOGGER.debug("Received user input: %s", user_input)

            username = user_input["Username"]
            password = user_input["Password"]

            session = aioboto3.Session()

            try:
                async with session.client('cognito-idp', region_name='us-east-2') as client:
                    # Log when starting SRP auth
                    _LOGGER.debug("Starting SRP authentication")

                    aws_srp = AWSSRP(
                        username=username,
                        password=password,
                        pool_id=PoolId,
                        client_id=ClientId,
                        client=client
                    )

                    auth_params = aws_srp.get_auth_params()
                    _LOGGER.debug("Generated auth params: %s", auth_params)

                    response = await client.initiate_auth(
                        ClientId=ClientId,
                        AuthFlow='USER_SRP_AUTH',
                        AuthParameters=auth_params
                    )

                    _LOGGER.debug("Received auth response: %s", response)

                    if response.get('ChallengeName') == 'PASSWORD_VERIFIER':
                        _LOGGER.debug("Processing password challenge")

                        challenge_responses = aws_srp.process_challenge(
                            response['ChallengeParameters'],    # This should include PASSWORD_CLAIM_SECRET_BLOCK, PASSWORD_CLAIM_SIGNATURE, TIMESTAMP, USERNAME (as a UUID)
                            auth_params
                        )
                        _LOGGER.debug("ChallengeParameters: %s", response['ChallengeParameters'])

                        response = await client.respond_to_auth_challenge(
                            ClientId=ClientId,
                            ChallengeName='PASSWORD_VERIFIER',
                            ChallengeResponses=challenge_responses
                        )

                        _LOGGER.debug("Challenge response received: %s", response)

                    # Extract tokens
                    auth_result = response['AuthenticationResult']
                    access_token = auth_result['AccessToken']
                    expiry = timedelta(seconds=auth_result['ExpiresIn']) + datetime.now()
                    id_token = auth_result['IdToken']
                    refresh_token = auth_result['RefreshToken']

                    # Log success
                    _LOGGER.debug("Authentication successful, tokens retrieved. Getting System ID")
                    
                    system_id = await self._get_system_id(id_token)

                    # Store tokens and additional data
                    return self.async_create_entry(
                        title="INSNRG Chlorinator",
                        data={
                            "Username": username,
                            "access_token": access_token,
                            "expiry": expiry,
                            "id_token": id_token,
                            "refresh_token": refresh_token,
                            "system_id": system_id,
                            "high_ph": user_input["high_ph"],
                            "low_ph": user_input["low_ph"],
                            "high_orp": user_input["high_orp"],
                            "low_orp": user_input["low_orp"]
                        }
                    )
            except ClientError as e:
                _LOGGER.error(f"Authentication failed: {e}")
                errors["base"] = "auth_failed"
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {e}")
                errors["base"] = "auth_failed"

        # Show form again if authentication failed
        schema = vol.Schema({
            vol.Required("Username", default=""): str,
            vol.Required("Password", default=""): str,
            vol.Required("high_ph", default=7.8): vol.Coerce(float),
            vol.Required("low_ph", default=7.0): vol.Coerce(float),
            vol.Required("high_orp", default=800): vol.Coerce(int),
            vol.Required("low_orp", default=600): vol.Coerce(int),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _get_system_id(self, id_token):
        headers = {
            "Authorization": f"Bearer {id_token}"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with async_timeout.timeout(10):
                    async with session.post(API_SystemID_URL, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            _LOGGER.debug("Obtaining SystemID")
            
                            # Check if the response contains the 'data' field and it's a list with at least one item
                            if "data" in data and isinstance(data["data"], list):
                                # Iterate through the items to find the first one with isActive == True
                                for item in data["data"]:
                                    if item.get("isActive"):
                                        system_id = item.get("systemId")
                                        _LOGGER.debug("Found Active systemId: %s", system_id)
                                        return system_id
                            _LOGGER.warning("No systemId found in response data.")
                            return None  # Return None if no systemId is found
                        else:
                            _LOGGER.error("Error fetching data from API: %s", await response.text())
            except Exception as err:
                _LOGGER.error(f"Exception during chlorinator SystemID retrieval: {err}")
