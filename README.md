# Power Max Tracker Integration for Home Assistant

The **Power Max Tracker** integration for Home Assistant tracks the maximum hourly average power values from a specified power sensor, with optional gating by a binary sensor. It creates sensors to display the top power values in kilowatts (kW) and a source sensor that mirrors the input sensor in watts (W), ignoring negative values and setting to `0` when the binary sensor is off.

## Features
- **Max Power Sensors**: Creates `num_max_values` sensors (e.g., `sensor.max_power_1_<entry_id>`, `sensor.max_power_2_<entry_id>`) showing the top hourly average power values in kW, rounded to 2 decimal places.
- **Source Power Sensor**: Creates a sensor (e.g., `sensor.power_max_source_<entry_id>`) that tracks the source sensor's state in watts, setting to `0` for negative values or when the binary sensor is off/unavailable.
- **Hourly Updates**: Updates `max_values` at 1 minute past each hour using hourly average statistics from the source sensor.
- **Negative Value Filtering**: Ignores negative power values in both the source sensor and max value calculations.
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

## Usage
- **Entities Created**:
  - `sensor.max_power_<index>_<entry_id>`: Top `num_max_values` hourly average power values in kW (e.g., `sensor.max_power_1_01K6ABFNPK61HBVAN855WBHXBG`).
  - `sensor.power_max_source_<entry_id>`: Tracks the source sensor in watts, `0` if negative or binary sensor is off/unavailable.
- **Service**: Call `power_max_tracker.update_max_values` via Developer Tools > Services to recalculate max values from midnight.
- **Updates**: Max sensors update at 1 minute past each hour or after calling the service. The source sensor updates in real-time when the binary sensor is `"on"`.

## License
MIT License. See `LICENSE` file for details.