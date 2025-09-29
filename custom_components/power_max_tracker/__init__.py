"""Power Max Tracker integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_SOURCE_SENSOR, CONF_MONTHLY_RESET, CONF_NUM_MAX_VALUES, CONF_BINARY_SENSOR
from .coordinator import PowerMaxCoordinator
from .sensor import MaxPowerSensor, SourcePowerSensor  # Import sensor after coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Power Max Tracker integration from YAML."""
    if DOMAIN not in config:
        # Register service globally
        async def update_max_values_service(call: ServiceCall) -> None:
            """Service to update max values from midnight."""
            _LOGGER.debug("Running update_max_values_service")
            for entry_id, coord in hass.data.get(DOMAIN, {}).items():
                if isinstance(coord, PowerMaxCoordinator):
                    await coord.async_update_max_values_from_midnight()

        hass.services.async_register(DOMAIN, "update_max_values", update_max_values_service)
        return True

    for conf in config[DOMAIN]:
        # Validate configuration
        if not isinstance(conf.get(CONF_NUM_MAX_VALUES, 2), int) or not (1 <= conf.get(CONF_NUM_MAX_VALUES, 2) <= 10):
            _LOGGER.error("num_max_values must be an integer between 1 and 10")
            continue

        # Create a config entry programmatically
        entry_data = {
            CONF_SOURCE_SENSOR: conf.get(CONF_SOURCE_SENSOR),
            CONF_NUM_MAX_VALUES: conf.get(CONF_NUM_MAX_VALUES, 2),
            CONF_MONTHLY_RESET: conf.get(CONF_MONTHLY_RESET, False),
            CONF_BINARY_SENSOR: conf.get(CONF_BINARY_SENSOR),
            "max_values": [0.0] * conf.get(CONF_NUM_MAX_VALUES, 2)
        }
        hass.async_create_task(
            hass.config_entries.async_add(
                ConfigEntry(
                    version=1,
                    domain=DOMAIN,
                    title=f"Power Max Tracker ({conf.get(CONF_SOURCE_SENSOR, 'unknown').split('.')[-1]})",
                    data=entry_data,
                    source="yaml",
                    options={},
                )
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the integration from a config entry."""
    try:
        coordinator = PowerMaxCoordinator(hass, entry)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator
        await coordinator.async_setup()

        # Forward setup to sensor platform asynchronously
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
    except Exception as err:
        raise ConfigEntryNotReady(f"Error setting up Power Max Tracker: {err}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_unload()
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False