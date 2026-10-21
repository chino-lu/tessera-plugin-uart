# UART link

Exchanges sensors and binary sensors between two ESP boards over a serial line, without Wi-Fi or Home Assistant between
them. The screen's two free pins go to an RS485 transceiver (or straight to the other board's UART), and the plugin
speaks ESPHome's own **packet transport** protocol over the line: the very protocol of ESPHome's `packet_transport`
platform (`platform: uart`), framed as asynchronous HDLC with a CRC-16. So a Tessera screen and any other ESPHome node —
a KC868, a plain ESP32, another screen — send each other states directly, multi-drop RS485 included.

Both directions work:

- **From the peer.** The other board broadcasts its states as ESPHome's packet transport does (`sensors:` and
  `binary_sensors:` under `packet_transport:`). This plugin reads them: the packets count, and the last one's time shows
  on the tile. To bring the peer's values onto this screen as entities, the peer can also publish them to Home
  Assistant, and this screen reads them there.
- **To the peer.** The states this screen sends are the entities you list under `out_sensors` and
  `out_binary_sensors` of the `uart_link:` component in the screen's Override YAML (any sensor of the screen, with an
  optional `broadcast_id` for the id the peer receives). The peer receives them as its own `packet_transport` sensors:
  `sensor: - platform: packet_transport, provider: <this screen's name>, remote_id: <the broadcast id>`.

The link's own health is a **UART link** tile on a page (a dot that says the peer was heard, the time of the last
packet, and the two counters), a **UART link** switch to pause the link without a build, and in Home Assistant on the
screen's device: **UART link status** (listening, paused, or waiting for the peer), **UART link packets received** and
**UART link packets sent** for a graph of the link. All of them are on the screen itself too: hold the top bar,
**Settings**, **Plugins**, **UART link**.

## Which screens

Every screen: the plugin asks for two free pins when it is added, so it fits any board. The pins are the screen's own
GPIO, to an RS485 transceiver beside it (TX to DI, RX from RO, and the transceiver's direction pin to a third pin of
yours, or tied to transmit while sending). A bare UART peer (no RS485) works over short wires at the same settings.

## Set up

1. In Tessera, open **Plugins**, choose **UART link** and tick your screen. Give it the **TX pin** and the **RX pin** of
   the RS485 transceiver (free pins of the board), the **Baud rate** (115200 by default, the same as the peer's), and
   the **Peer name**: the other board's ESPHome name, such as `kc868-aio`. Leave it empty to listen to every node on the
   bus. Add the plugin; the screen builds once.
2. On the other board, configure ESPHome's own packet transport over its UART, with the same baud rate:
   `uart:` with its pins, then `packet_transport: platform: uart, uart_id: <its uart>`, and the states to broadcast
   under `sensors:` and `binary_sensors:` (with `broadcast_id` where the peer should receive another id). Its
   `update_interval` is how often it sends its full state; a change of a listed state is sent at once.
3. Wire the two boards: the transceivers' A and B lines together (A to A, B to B), and a common ground.
4. In Layout, place the **UART link** tile from the library's Plugins group. Its dot turns green when a packet of the
   peer arrived, and the tile says when the last one came and how many packets went both ways.
5. To send this screen's own states to the peer, add them in the screen's Override YAML, under the `uart_link:`
   component (this is ESPHome YAML, not a setting):

   ```yaml
   uart_link:
     out_sensors:
       - id: my_sensor            # any sensor of the screen
         broadcast_id: room_temp  # optional: the id the peer receives
     out_binary_sensors:
       - id: my_binary_sensor
   ```

   The peer receives them as `sensor: - platform: packet_transport` with `provider:` the screen's ESPHome name and
   `remote_id:` the broadcast id.

## Good to know

- The peer's name is in clear text in every packet (ESPHome's protocol writes it there), and without an encryption key the
  states are clear text too. On a private RS485 bus that is fine; do not put the bus where others can read it.
- The plugin sends a packet when a listed state changes, and the peer's full state arrives on its own
  `update_interval` (15 seconds in ESPHome's default). The tile's "last packet" follows that.
- Pausing the link (**UART link** off) stops the reading and the sending; the screen keeps its Wi-Fi and Home
  Assistant connection, only the serial link rests.
- It adds about 24 KB to the firmware.
- Had a `uart:` block or a `packet_transport:` block in the Override YAML for the same pins? Remove it first, or the
  build finds the UART twice.

## Privacy

The plugin opens no connection to the network: the packets go over the serial line to the peer, and nothing leaves the
two boards. It reads no Home Assistant entity and calls no Home Assistant action.
