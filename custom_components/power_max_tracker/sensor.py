import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_NUM_MAX_VALUES, CONF_SOURCE_SENSOR, CONF_BINARY_SENSOR
from .coordinator import PowerMaxCoordinator

_LOGGER = logging.getLogger(__name__)

class GatedSensorEntity(SensorEntity):
    """Base class for sensors gated by a binary sensor."""

    def __init__(self, entry: ConfigEntry):
        """Initialize."""
        super().__init__()
        self._binary_sensor = entry.data.get(CONF_BINARY_SENSOR)

    def _can_update(self):
        """Check if the sensor can update based on binary sensor state."""
        if not self._binary_sensor:
            return True
        state = self.hass.states.get(self._binary_sensor)
        return state is not None and state.state == "on"

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
    # Add average max power sensor
    average_max_sensor = AverageMaxPowerSensor(coordinator, entry)
    sensors.append(average_max_sensor)
    # Add SourcePowerSensor
    source_sensor = SourcePowerSensor(coordinator, entry)
    sensors.append(source_sensor)
    # Add HourlyAveragePowerSensor
    hourly_average_power_sensor = HourlyAveragePowerSensor(coordinator, entry)
    sensors.append(hourly_average_power_sensor)
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

class AverageMaxPowerSensor(SensorEntity):
    """Sensor for the average of all max hourly average power values."""

    def __init__(self, coordinator: PowerMaxCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__()
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "Average Max Hourly Average Power"
        self._attr_unique_id = f"{entry.entry_id}_average_max"
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
        if max_values:
            return round(sum(max_values) / len(max_values), 2)
        return 0.0

class SourcePowerSensor(GatedSensorEntity):
    """Sensor that tracks the source sensor state, gated by binary sensor."""

    def __init__(self, coordinator: PowerMaxCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(entry)
        self._coordinator = coordinator
        self._entry = entry
        self._source_sensor = entry.data[CONF_SOURCE_SENSOR]
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

    @property
    def native_value(self):
        """Return the state."""
        return self._state


class HourlyAveragePowerSensor(GatedSensorEntity):
    """Sensor for hourly average power in kW so far the current hour."""

    def __init__(self, coordinator: PowerMaxCoordinator, entry: ConfigEntry):
        """Initialize."""
        super().__init__(entry)
        self._coordinator = coordinator
        self._entry = entry
        self._source_sensor = entry.data[CONF_SOURCE_SENSOR]
        self._attr_name = f"Hourly Average Power {self._source_sensor.split('.')[-1]}"
        self._attr_unique_id = f"{entry.entry_id}_hourly_average_power"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_should_poll = False
        self._accumulated_energy = 0.0
        self._last_power = 0.0
        self._last_time = None
        self._hour_start = None

    async def async_added_to_hass(self):
        """Handle entity added to hass."""
        async def _async_hour_start(now):
            """Reset at the start of each hour."""
            self._accumulated_energy = 0.0
            self._last_power = 0.0
            self._last_time = now
            self._hour_start = now
            self.async_write_ha_state()

        # Track hour changes
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                _async_hour_start,
                hour=None,
                minute=0,
                second=0,
            )
        )

        # Initialize
        await _async_hour_start(dt_util.utcnow())

        async def _async_state_changed(event):
            """Handle state changes of source or binary sensor."""
            now = dt_util.utcnow()
            if self._last_time is None:
                self._last_time = now
                return
            if self._can_update():
                source_state = self.hass.states.get(self._source_sensor)
                if source_state is not None and source_state.state not in ("unavailable", "unknown"):
                    try:
                        current_power = float(source_state.state)
                        if current_power < 0:
                            current_power = 0.0
                        delta_seconds = (now - self._last_time).total_seconds()
                        if delta_seconds > 0:
                            # Average power in W
                            avg_power = (self._last_power + current_power) / 2
                            # Energy in kWh
                            delta_energy = avg_power * delta_seconds / 3600000
                            self._accumulated_energy += delta_energy
                        self._last_power = current_power
                        self._last_time = now
                    except (ValueError, TypeError):
                        _LOGGER.warning(f"Invalid state for {self._source_sensor}: {source_state.state}")
                        self._last_power = 0.0
                else:
                    _LOGGER.debug(f"Source sensor {self._source_sensor} unavailable or unknown")
                    self._last_power = 0.0
            else:
                self._last_power = 0.0
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

    @property
    def native_value(self):
        """Return the state."""
        if self._hour_start is None:
            return 0.0
        now = dt_util.utcnow()
        elapsed_hours = (now - self._hour_start).total_seconds() / 3600
        if elapsed_hours > 0:
            return round(self._accumulated_energy / elapsed_hours, 3)
        return 0.0
