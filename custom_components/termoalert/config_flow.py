import voluptuous as vol

from homeassistant.config_entries import ConfigFlow

from .parser import bloc_key, street_key

DOMAIN = "termoalert"
SCHEMA = vol.Schema({vol.Required("strada"): str, vol.Optional("bloc"): str})


class TermoAlertConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            strada = user_input["strada"].strip()
            bloc = (user_input.get("bloc") or "").strip()
            if not street_key(strada):
                errors["strada"] = "invalid_street"
            else:
                await self.async_set_unique_id(f"{street_key(strada)}|{bloc_key(bloc)}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{strada}, bl. {bloc}" if bloc else strada,
                    data={"strada": strada, "bloc": bloc},
                )
        return self.async_show_form(
            step_id="user", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input), errors=errors)
