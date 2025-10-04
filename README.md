[![power_max_tracker](https://img.shields.io/github/release/perosb/power_max_tracker/all.svg?label=current%20release)](https://github.com/perosb/power_max_tracker) [![downloads](https://img.shields.io/github/downloads/perosb/power_max_tracker/total?label=downloads)](https://github.com/perosb/power_max_tracker)

# Power Max Tracker Integration for Home Assistant

The **Power Max Tracker** integration for Home Assistant tracks the maximum hourly average power values from a specified power sensor, with optional gating by a binary sensor. It creates sensors to display the top power values in kilowatts (kW), their average, a source sensor that mirrors the input sensor in watts (W), and an hourly average power sensor, all ignoring negative values and setting to `0` when the binary sensor is off.

## Features
- **Max Power Sensors**: Creates `num_max_values` sensors (e.g., `sensor.max_hourly_average_power_1_<entry_id>`, `sensor.max_hourly_average_power_2_<entry_id>`) showing the top hourly average power values in kW, rounded to 2 decimal places.
- **Average Max Power Sensor**: Creates a sensor (e.g., `sensor.average_max_hourly_average_power_<entry_id>`) showing the average of all max hourly average power values in kW.
- **Source Power Sensor**: Creates a sensor (e.g., `sensor.power_max_source_<entry_id>`) that tracks the source sensor's state in watts, setting to `0` for negative values or when the binary sensor is off/unavailable.
- **Hourly Average Power Sensor**: Creates a sensor (e.g., `sensor.hourly_average_power_<entry_id>`) that calculates the average power in kW so far in the current hour based on the source sensor's power, gated by the binary sensor, with periodic updates to account for 0W periods.
- **Hourly Updates**: Updates `max_values` at 1 minute past each hour using hourly average statistics from the source sensor.
- **Negative Value Filtering**: Ignores negative power values in all sensors.
- **Binary Sensor Gating**: Only updates when the binary sensor (if configured) is `"on"`.
- **Monthly Reset**: Optionally resets `max_values` to `0` on the 1st of each month.
- **Multiple Config Entries**: Supports multiple source sensors with separate max value tracking.
- **Service**: Provides the `power_max_tracker.update_max_values` service to recalculate max values from midnight to the current hour.

## Installation
1. **Via HACS**:
   - Add `https://github.com/perosb/power_max_tracker` as a custom repository in HACS.
   - Install the `Power Max Tracker` integration.
   - Restart Home Assistant.

2. **Manual Installation**:
   - Download the latest release from `https://github.com/perosb/power_max_tracker`.
   - Extract the `power_max_tracker` folder to `/config/custom_components/`.
   - Restart Home Assistant.

## Configuration
Add the integration via the Home Assistant UI or `configuration.yaml`.

### Example `configuration.yaml`
```yaml
power_max_tracker:
  - source_sensor: sensor.power_sensor
    num_max_values: 2
    monthly_reset: false
    binary_sensor: binary_sensor.power_enabled
  - source_sensor: sensor.power_another_source
    num_max_values: 3
    monthly_reset: true
```

### Configuration Options
- `source_sensor` (required): The power sensor to track (e.g., `sensor.power_sensor`), must provide watts (W).
- `num_max_values` (optional, default: 2): Number of max power sensors (1–10).
- `monthly_reset` (optional, default: `false`): Reset max values to `0` on the 1st of each month.
- `binary_sensor` (optional): A binary sensor (e.g., `binary_sensor.power_enabled`) to gate updates; only updates when `"on"`.

### Example Binary Sensor Template
If you want to gate the power tracking based on time (e.g., only during high peak hours in certain months), create a template binary sensor in your `configuration.yaml` and reference it in the `binary_sensor` option. Here's an example that activates during weekdays (Mon-Fri) from 7 AM to 8 PM in the months of November through March:

```yaml
template:
  - binary_sensor:
      - name: "Power Tracking Gate"
        state: >
          {% set current_month = now().month %}
          {% set current_day = now().weekday() %}
          {% set current_hour = now().hour %}
          {% if current_month in [11, 12, 1, 2, 3] and current_day in [0, 1, 2, 3, 4] and current_hour >= 7 and current_hour < 20 %}
            True
          {% else %}
            False
          {% endif %}
```

Then, configure the integration to use this sensor:
```yaml
power_max_tracker:
  - source_sensor: sensor.power_sensor
    binary_sensor: binary_sensor.power_tracking_gate
```

## Usage
- **Entities Created**:
  - `sensor.max_hourly_average_power_<index>_<entry_id>`: Top `num_max_values` hourly average power values in kW (e.g., `sensor.max_hourly_average_power_1_01K6ABFNPK61HBVAN855WBHXBG`).
  - `sensor.average_max_hourly_average_power_<entry_id>`: Average of all max hourly average power values in kW.
  - `sensor.power_max_source_<entry_id>`: Tracks the source sensor in watts, `0` if negative or binary sensor is off/unavailable.
  - `sensor.hourly_average_power_<entry_id>`: Average power in kW so far in the current hour, with periodic updates for 0W periods.
- **Service**: Call `power_max_tracker.update_max_values` via Developer Tools > Services to recalculate max values from midnight.
- **Updates**: Max sensors update at 1 minute past each hour or after calling the service. The source and hourly average sensors update in real-time when the binary sensor is `"on"`, with additional periodic updates for the hourly average sensor.

## Important Notes
- **Renaming Source Sensor**: If the `source_sensor` is renamed (e.g., from `sensor.power_sensor` to `sensor.new_power_sensor`), the integration will stop tracking it. Update the configuration with the new entity ID and restart Home Assistant to restore functionality.

## License
MIT License. See `LICENSE` file for details.