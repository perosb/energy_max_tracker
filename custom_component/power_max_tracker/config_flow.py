import uuid
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_SOURCE_SENSOR, CONF_MONTHLY_RESET, CONF_NUM_MAX_VALUES, CONF_BINARY_SENSOR

class PowerMaxTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Validate num_max_values
            num_max = user_input.get(CONF_NUM_MAX_VALUES, 2)  # Fallback to default
            if num_max < 1 or num_max > 10:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(),
                    errors={CONF_NUM_MAX_VALUES: "Number of max values must be an integer between 1 and 10"}
                )

            # Generate a unique title based on the source sensor and a random suffix
            source_sensor = user_input[CONF_SOURCE_SENSOR]
            title = f"Power Max Tracker ({source_sensor.split('.')[-1]}-{str(uuid.uuid4())[:8]})"
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
        )

    def _get_schema(self):
        """Return the data schema for the form."""
        return vol.Schema(
            {
                vol.Required(CONF_SOURCE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="power"
                    )
                ),
                vol.Optional(CONF_MONTHLY_RESET, default=False): selector.BooleanSelector(),
                vol.Required(CONF_NUM_MAX_VALUES, default=2): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_BINARY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
            }
        )