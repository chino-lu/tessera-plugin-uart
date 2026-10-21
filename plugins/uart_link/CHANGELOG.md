# Changelog

## 0.1.0
- First version: ESPHome's packet transport over a UART on the screen's two free pins, so two ESP boards exchange sensors and binary sensors directly, RS485 multi-drop included.
- The pins, the baud rate and the peer's name are asked when the plugin is added; a build without them works on GPIO4 and GPIO5 at 115200.
- The link's health is a tile (last packet, packets received and sent), a setting to pause the link without a build, and a status text sensor and two counters in Home Assistant.
- Both directions, configured in the screen's Override YAML with `uart_link_entities:`: send the screen's own states with `out_sensors`/`out_binary_sensors` (the peer receives them as its own `packet_transport` sensors), and receive the peer's states with `in_sensors`/`in_binary_sensors` (template entities of the screen, by the peer's `remote_id`).
- Every 15 seconds the link sends its full state, so a peer that restarted catches up without waiting for a change.
