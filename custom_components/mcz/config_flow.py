import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN


class MCZConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    "device_id": user_input["device_id"],
                    "name": user_input["name"],
                },
            )

        data_schema = vol.Schema({
            vol.Required("device_id"): str,
            vol.Required("name", default="Poêle MCZ"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
