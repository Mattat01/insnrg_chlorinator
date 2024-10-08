import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

@callback
def configured_instances(hass):
    return {entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)}

class InsnrgChlorinatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validate user input here
            return self.async_create_entry(title="INSNRG Chlorinator", data=user_input)

        schema = vol.Schema({
            vol.Required("bearer_token"): str,
            vol.Required("system_id"): str,  # Add system ID
            vol.Required("high_ph", default=7.8): vol.Coerce(float),
            vol.Required("low_ph", default=7.0): vol.Coerce(float),
            vol.Required("high_orp", default=800): vol.Coerce(int),
            vol.Required("low_orp", default=600): vol.Coerce(int),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
