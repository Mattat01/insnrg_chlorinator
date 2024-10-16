import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, ClientId
import aioboto3

_LOGGER = logging.getLogger(__name__)

@callback
def configured_instances(hass):
    return {entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)}

class InsnrgChlorinatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Extract username, password, and system_id
            username = user_input["Username"]
            password = user_input["Password"]
            system_id = user_input["system_id"]

            session = aioboto3.Session()

            async with session.client('cognito-idp', region_name='us-east-2') as client:
                try:
                    # Make async calls with the client
                    response = await client.initiate_auth(
                        ClientId=ClientId,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={
                            'USERNAME': username,
                            'PASSWORD': password
                        }
                    )

                    # Extract tokens
                    access_token = response['AuthenticationResult']['AccessToken']
                    id_token = response['AuthenticationResult']['IdToken']
                    refresh_token = response['AuthenticationResult']['RefreshToken']

                    # Store tokens and additional data
                    return self.async_create_entry(
                        title="INSNRG Chlorinator",
                        data={
                            "Username": username,
                            "access_token": access_token,
                            "id_token": id_token,
                            "refresh_token": refresh_token,
                            "system_id": system_id,
                            "high_ph": user_input["high_ph"],
                            "low_ph": user_input["low_ph"],
                            "high_orp": user_input["high_orp"],
                            "low_orp": user_input["low_orp"]
                        }
                    )
                except client.exceptions.NotAuthorizedException:
                    errors["base"] = "auth_failed"
                except Exception as e:
                    _LOGGER.error(f"Authentication failed: {e}")
                    errors["base"] = "auth_failed"

        # Show the form again if authentication failed
        schema = vol.Schema({
            vol.Required("Username", default=""): str,
            vol.Required("Password", default=""): str,
            vol.Required("system_id", default="insnrgbcddc2f2f2ed"): str,
            vol.Required("high_ph", default=7.8): vol.Coerce(float),
            vol.Required("low_ph", default=7.0): vol.Coerce(float),
            vol.Required("high_orp", default=800): vol.Coerce(int),
            vol.Required("low_orp", default=600): vol.Coerce(int),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
