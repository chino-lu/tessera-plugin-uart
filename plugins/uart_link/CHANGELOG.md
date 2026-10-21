# Changelog

## 0.1.0
- First version: ESPHome's packet transport over a UART on the screen's two free pins, so two ESP boards exchange sensors and binary sensors directly, RS485 multi-drop included.
- The pins, the baud rate and the peer's name are asked when the plugin is added; a build without them works on GPIO4 and GPIO5 at 115200.
- The link's health is a tile (last packet, packets received and sent), a setting to pause the link without a build, and a status text sensor and two counters in Home Assistant.
- Send this screen's own states with `out_sensors` and `out_binary_sensors` of the `uart_link:` component; the peer receives them as its own `packet_transport` sensors.
