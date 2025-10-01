import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, CONF_NUM_MAX_VALUES, CONF_SOURCE_SENSOR, CONF_BINARY_SENSOR
from .coordinator import PowerMaxCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    num_max_values = int(entry.data.get(CONF_NUM_MAX_VALUES, 2))  # Cast to int
    sensors = [
        MaxPowerSensor(coordinator, idx, f"Max Hourly Average Power {idx + 1}")
        for idx in range(num_max_values)
    ]
    # Add SourcePowerSensor
    source_sensor = SourcePowerSensor(coordinator, entry)
    sensors.append(source_sensor)
    # Add CurrentHourlyEnergySensor
    energy_sensor = CurrentHourlyEnergySensor(coordinator, entry)
    sensors.append(energy_sensor)
    async_add_entities(sensors, update_before_add=True)
    for sensor in sensors:
        coordinator.add_entity(sensor)
        _LOGGER.debug(f"Registered sensor {sensor._attr_name} with coordinator, unique_id {sensor._attr_unique_id}, entity_id {sensor.entity_id}")

class MaxPowerSensor(SensorEntity):
    """Sensor for max hourly average power in kW."""

    def __init__(self, coordinator: PowerMaxCoordinator, index: int, name: str):
        """Initialize."""
        super().__init__()
        self._coordinator = coordinator
        self._index = index
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_max_values_{index + 1}"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:chart-line"
        self._attr_should_poll = False  # Updated via coordinator
        self._attr_force_update = True  # Force state updates

    @property
    def native_value(self):
        """Return the state."""
        max_values = self._coordinator.max_values
        return round(max_values[self._index], 2) if len(max_values) > self._index else 0.0

class SourcePowerSensor(SensorEntity):
    """Sensor that tracks the source sensor state, gated by binary sensor."""

    def __init__(self, coordinator: PowerMaxCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__()
        self._coordinator = coordinator
        self._entry = entry
        self._source_sensor = entry.data[CONF_SOURCE_SENSOR]
        self._binary_sensor = entry.data.get(CONF_BINARY_SENSOR)
        self._attr_name = f"Power Max Source {self._source_sensor.split('.')[-1]}"
        self._attr_unique_id = f"{entry.entry_id}_source"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:power"
        self._attr_should_poll = False  # Updated via state changes
        self._state = 0.0

    async def async_added_to_hass(self):
        """Handle entity added to hass."""
        async def _async_state_changed(event):
            """Handle state changes of source or binary sensor."""
            if self._can_update():
                source_state = self.hass.states.get(self._source_sensor)
                if source_state is not None and source_state.state not in ("unavailable", "unknown"):
                    try:
                        value = float(source_state.state)
                        self._state = max(0.0, value)  # Ignore negative values
                    except (ValueError, TypeError):
                        _LOGGER.warning(f"Invalid state for {self._source_sensor}: {source_state.state}")
                        self._state = 0.0
                else:
                    _LOGGER.debug(f"Source sensor {self._source_sensor} unavailable or unknown")
                    self._state = 0.0
            else:
                self._state = 0.0
            self.async_write_ha_state()

        # Track state changes of source and binary sensors
        sensors = [self._source_sensor]
        if self._binary_sensor:
            sensors.append(self._binary_sensor)
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, sensors, _async_state_changed
            )
        )

    def _can_update(self):
        """Check if the sensor can update based on binary sensor state."""
        if not self._binary_sensor:
            return True
        state = self.hass.states.get(self._binary_sensor)
        return state is not None and state.state == "on"

    @property
    def native_value(self):
        """Return the state."""
        return self._state

class CurrentHourlyEnergySensor(SensorEntity):
    """Sensor for average kWh usage so far in the current hour."""

    def __init__(self, coordinator: PowerMaxCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__()
        self._coordinator = coordinator
        self._entry = entry
        self._source_sensor = entry.data[CONF_SOURCE_SENSOR]
        self._binary_sensor = entry.data.get(CONF_BINARY_SENSOR)
        self._attr_name = f"Current Hourly Energy {self._source_sensor.split('.')[-1]}"
        self._attr_unique_id = f"{entry.entry_id}_current_hourly_energy"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:lightning-bolt-circle"
        self._attr_should_poll = False  # Updated via state changes
        self._state = 0.0
        self._last_state = None
        self._last_update = None

    async def async_added_to_hass(self):
        """Handle entity added to hass."""
        async def _async_state_changed(event: Event):
            """Handle state changes of source sensor."""
            if not self._can_update():
                self._state = 0.0
                self._last_state = None
                self._last_update = None
                self.async_write_ha_state()
                return

            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in ("unavailable", "unknown"):
                _LOGGER.debug(f"Source sensor {self._source_sensor} unavailable or unknown")
                self._state = 0.0
                self._last_state = None
                self._last_update = None
            else:
                try:
                    power_watts = float(new_state.state)
                    if power_watts < 0:
                        _LOGGER.debug(f"Skipping negative power: {power_watts} W")
                        power_watts = 0.0
                    current_time = new_state.last_updated

                    if self._last_state is not None and self._last_update is not None:
                        time_diff_seconds = (current_time - self._last_update).total_seconds()
                        energy_increment_kwh = (power_watts / 1000.0 + self._last_state / 1000.0) * (time_diff_seconds / 3600.0) / 2.0
                        self._state += energy_increment_kwh
                    else:
                        self._state = 0.0  # Reset at the start of tracking or after unavailability

                    self._last_state = power_watts
                    self._last_update = current_time
                    self._state = round(self._state, 2)
                except (ValueError, TypeError):
                    _LOGGER.warning(f"Invalid state for {self._source_sensor}: {new_state.state}")
                    self._state = 0.0
                    self._last_state = None
                    self._last_update = None

            self.async_write_ha_state()

        # Track state changes of source sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_sensor], _async_state_changed
            )
        )

    def _can_update(self):
        """Check if the sensor can update based on binary sensor state."""
        if not self._binary_sensor:
            return True
        state = self.hass.states.get(self._binary_sensor)
        return state is not None and state.state == "on"

    @property
    def native_value(self):
        """Return the state."""
        return self._state

    async def async_will_remove_from_hass(self):
        """Handle entity removed from hass."""
        pass  # No listeners to clean up since using state change event