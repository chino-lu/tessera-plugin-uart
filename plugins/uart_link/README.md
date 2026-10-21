# UART link

Exchanges sensors and binary sensors between two ESP boards over a serial line, without Wi-Fi or Home Assistant between
them. The screen's two free pins go to an RS485 transceiver (or straight to the other board's UART), and the plugin
speaks ESPHome's own **packet transport** protocol over the line: the very protocol of ESPHome's `packet_transport`
platform (`platform: uart`), framed as asynchronous HDLC with a CRC-16. So a Tessera screen and any other ESPHome node —
a KC868, a plain ESP32, another screen — send each other states directly, multi-drop RS485 included.

Both directions work, configured in the screen's Override YAML with the `uart_link_entities:` component (the entities
the link sends and receives, each by the id the other side knows it by):

- **From the peer.** The other board broadcasts its states as ESPHome's packet transport does (`sensors:` and
  `binary_sensors:` under `packet_transport:`, each with a `broadcast_id`). This plugin reads them and publishes them
  into the entities you list under `in_sensors:` and `in_binary_sensors:` — template sensors of the Override YAML, the
  same ones your alarm display used (`rx_smoke`, `rx_siren`, ...). They reach Home Assistant like any sensor of the
  screen, and every normal tile can show them.
- **To the peer.** The states this screen sends are the entities you list under `out_sensors:` and
  `out_binary_sensors:` (any sensor of the screen, with an optional `broadcast_id` for the id the peer receives). The
  peer receives them as its own `packet_transport` sensors:
  `sensor: - platform: packet_transport, provider: <this screen's name>, remote_id: <the broadcast id>`.

A change of a listed state is sent at once; every 15 seconds the link also sends its full state, so a peer that
restarted catches up without waiting for a change.

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
5. In the screen's **Override YAML**, register the entities the link carries, and the template entities that receive
   the peer's states (this is ESPHome YAML, not a setting):

   ```yaml
   # The states this screen sends to the peer (commands of the display, for example).
   binary_sensor:
     - platform: template
       id: cmd_disarm
       internal: true
   # ... one for every command

   # The states the peer sends, received into template entities of this screen. The remote_id is the
   # broadcast_id the peer sends; the id is the entity on this screen (and in Home Assistant).
   binary_sensor:
     - platform: template
       id: rx_smoke
       name: "Smoke alarm"
   binary_sensor:
     - platform: template
       id: rx_siren
       name: "Siren"
   # ... one for every state

   uart_link_entities:
     link: uart_link
     out_binary_sensors:
       - id: cmd_disarm
         broadcast_id: cmd_disarm
       # ... one per command
     in_binary_sensors:
       - id: rx_smoke
         remote_id: smoke_state
       - id: rx_siren
         remote_id: siren_state
       # ... one per state
   ```

   The peer receives the screen's commands as `binary_sensor: - platform: packet_transport` with `provider:` the
   screen's ESPHome name and `remote_id:` the broadcast id. Numeric states work the same way with `sensor:` and
   `in_sensors:`/`out_sensors:`.

## An alarm display, like yours

This plugin is the Tessera form of the setup of a Waveshare ESP32-S3 display that talks to a KC868 over RS485. Your old
`waveshare.yml` used ESPHome's `packet_transport:` with `platform: uart`, binary sensors with `broadcast_id:` for the
commands (Display to KC868) and `binary_sensor: - platform: packet_transport` with `provider:`/`remote_id:` for the
states (KC868 to Display). This plugin speaks the same protocol, so the two boards keep working together, and the
Display becomes a Tessera screen with normal tiles.

**The KC868 (unchanged, stock ESPHome):**

```yaml
# kc868-aio.yaml (the peer; its name must match the Peer name of the screen's plugin)
uart:
  id: rs485_uart
  tx_pin: GPIO16
  rx_pin: GPIO15
  baud_rate: 115200

packet_transport:
  platform: uart
  uart_id: rs485_uart
  update_interval: 90s
  # States KC868 -> Display
  binary_sensors:
    - id: alarmo_disarmed
      broadcast_id: alarmo_disarmed
    - id: alarmo_triggered
      broadcast_id: alarmo_triggered
    - id: smoke
      broadcast_id: smoke_state
    - id: water
      broadcast_id: water_state
    - id: siren
      broadcast_id: siren_state
    - id: flash
      broadcast_id: flash_state
    - id: door_open
      broadcast_id: any_open
  # Commands Display -> KC868, received as packet_transport binary sensors
  providers:
    - name: alarmo-display

binary_sensor:
  - platform: packet_transport
    provider: alarmo-display
    id: rx_cmd_disarm
    remote_id: cmd_disarm
  # ... one per command: cmd_arm_away, cmd_arm_home, cmd_arm_night, cmd_siren_on, cmd_siren_off,
  #     cmd_flash_on, cmd_flash_off, cmd_smoke_mute, cmd_water_mute, cmd_sync_request
```

**The Tessera screen (your display), Override YAML:**

```yaml
# The commands the Display sends to the KC868 (the tile's keys publish these).
binary_sensor:
  - platform: template
    id: cmd_disarm
    internal: true
  - platform: template
    id: cmd_arm_away
    internal: true
  # ... one per command

# The states of the KC868, received into entities of this screen. They reach Home Assistant
# (binary_sensor.alarmo_display_smoke_alarm, ...) and every normal tile can show them.
binary_sensor:
  - platform: template
    id: rx_disarmed
    name: "Alarm disarmed"
  - platform: template
    id: rx_triggered
    name: "Alarm triggered"
  - platform: template
    id: rx_smoke
    name: "Smoke alarm"
  - platform: template
    id: rx_water
    name: "Water alarm"
  - platform: template
    id: rx_siren
    name: "Siren"
  - platform: template
    id: rx_flash
    name: "Flash light"
  - platform: template
    id: rx_any_open
    name: "Door or window open"

uart_link_entities:
  link: uart_link
  out_binary_sensors:
    - id: cmd_disarm
      broadcast_id: cmd_disarm
    - id: cmd_arm_away
      broadcast_id: cmd_arm_away
    # ... one per command
  in_binary_sensors:
    - id: rx_disarmed
      remote_id: alarmo_disarmed
    - id: rx_triggered
      remote_id: alarmo_triggered
    - id: rx_smoke
      remote_id: smoke_state
    - id: rx_water
      remote_id: water_state
    - id: rx_siren
      remote_id: siren_state
    - id: rx_flash
      remote_id: flash_state
    - id: rx_any_open
      remote_id: any_open
```

Then the alarm states are ordinary binary sensors on the screen: a tile for **Smoke alarm** shows red while it is on,
and a tile's tap action publishes `cmd_disarm` (one line in the tile's automation: `binary_sensor.template.publish`
on `cmd_disarm`, true for 100 ms, then false — the same pulse your old YAML sent with `publish_state`).

The protocol itself is tested on a computer against an independent implementation of ESPHome's framing:
`tests/test_transport.cpp` (see `tests/README.md`).

## Good to know

- The peer's name is in clear text in every packet (ESPHome's protocol writes it there), and without an encryption key the
  states are clear text too. On a private RS485 bus that is fine; do not put the bus where others can read it.
- The peer's full state arrives on its own `update_interval` (15 seconds in ESPHome's default). The tile's "last packet"
  follows that.
- Pausing the link (**UART link** off) stops the reading and the sending; the screen keeps its Wi-Fi and Home
  Assistant connection, only the serial link rests.
- It adds about 24 KB to the firmware.
- Had a `uart:` block or a `packet_transport:` block in the Override YAML for the same pins? Remove it first, or the
  build finds the UART twice.

## Privacy

The plugin opens no connection to the network: the packets go over the serial line to the peer, and nothing leaves the
two boards. It reads no Home Assistant entity and calls no Home Assistant action.
