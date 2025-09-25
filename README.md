# Hamilton City Council (Home Assistant Custom Integration)

Fetches bin collection dates from Hamilton City Council's FightTheLandFill API.

## Entities

- `sensor.hcc_bin_collection_date_red` (timestamp)
- `sensor.hcc_bin_collection_date_yellow` (timestamp)
- `sensor.hcc_bin_collection_info_last_fetch_date` (timestamp)
- `binary_sensor.hcc_bin_collection_info_fetch_status` (true when last fetch succeeded)
- `sensor.hcc_bin_collection_info_fetch_status_text` (`success`, `network_error`, `json_parsing`, `unexpected_error`)

## Behavior

- Values persist across failures; on failure only status entities update.
- Setup validates by performing one live fetch.

## Install

1. Copy this folder to `config/custom_components/hcc_bin`.
2. Restart Home Assistant.
3. Settings -> Devices & Services -> Add Integration -> "Hamilton City Council".
4. Enter your address exactly as HCC expects.
5. Adjust update interval in the integration Options.

## Notes

- Default interval: 60 minutes. Range 5..1440.
- Timestamps are provided as UTC in HA (device_class: `timestamp`).
