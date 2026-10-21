# Tests of the wire protocol

`test_transport.cpp` builds the real `components/uart_link/uart_link_transport.cpp` on a computer, against small stub
headers of ESPHome's `uart`, `sensor` and `binary_sensor` (`stubs/` beside it), and checks it against an independent
implementation of ESPHome's packet transport and HDLC framing, written from ESPHome's own sources:

- a change of a listed state sends exactly one packet, with the node's name, the sensor's float and the binary
  sensor's byte, and the independent decoder reads it back;
- the 15-second full-state resend carries every listed state;
- a packet from the peer (encoded by the independent encoder) publishes into the registered entities, and an
  unregistered remote id is ignored;
- a packet from another node on the bus, a packet with this node's own name, and a packet with a broken CRC are
  dropped;
- ids that contain the HDLC flag or escape byte survive the round trip;
- a paused link neither sends nor reads.

Run it:

```sh
g++ -std=c++17 -I stubs -I ../components/uart_link -o test_transport test_transport.cpp
./test_transport
```

The test is not part of the plugin's build: a plugin folder ships what a screen builds, and this file runs on a
computer only.
