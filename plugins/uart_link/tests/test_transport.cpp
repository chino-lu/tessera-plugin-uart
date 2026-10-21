// A host test of the real uart_link_transport.cpp: encode with the transport, decode with an independent
// implementation of ESPHome's packet_transport + HDLC framing, and the other way round.
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "esphome/core/application.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome { Application App; }
uint32_t millis() { static uint32_t t = 1000; return t += 10; }
namespace esphome { namespace log {} }

#include "uart_link_transport.cpp"

using namespace esphome;
using namespace esphome::uart_link;

// ---- independent decoder (from ESPHome's own sources) ----
static uint16_t crc16_ref(const uint8_t *data, size_t len) {
  uint16_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc ^= (uint16_t) data[i] << 8;
    for (int b = 0; b < 8; b++) crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

struct RefPacket { std::string from; std::vector<std::pair<std::string, float>> sensors; std::vector<std::pair<std::string, bool>> bsensors; };

// Un-HDLC a wire buffer into packets (independent implementation).
static std::vector<std::vector<uint8_t>> unhdlc(const std::vector<uint8_t> &wire) {
  std::vector<std::vector<uint8_t>> packets;
  std::vector<uint8_t> cur;
  bool started = false, esc = false;
  for (uint8_t b : wire) {
    if (b == 0x7E) {
      if (started && cur.size() > 2) packets.push_back(cur);
      started = true; cur.clear(); esc = false;
      continue;
    }
    if (!started) continue;
    if (b == 0x7D) { esc = true; continue; }
    if (esc) { b ^= 0x20; esc = false; }
    cur.push_back(b);
  }
  return packets;
}

static RefPacket decode_ref(const std::vector<uint8_t> &pkt) {
  RefPacket out;
  assert(pkt.size() >= 4);
  uint16_t magic = pkt[0] | (pkt[1] << 8);
  assert(magic == 0x4553);
  size_t nlen = pkt[2];
  out.from.assign((const char *) pkt.data() + 3, nlen);
  size_t pos = (3 + nlen + 3) & ~3;
  // verify CRC over payload
  uint16_t crc = crc16_ref(pkt.data(), pkt.size() - 2);
  assert(crc == (pkt[pkt.size() - 2] | (pkt[pkt.size() - 1] << 8)));
  assert(pkt[pos] == 1);  // DATA_KEY
  pos++;
  while (pos < pkt.size() - 2) {  // the last two bytes are the CRC
    uint8_t key = pkt[pos];
    if (key == 0) { pos++; continue; }  // ZERO_FILL_KEY: the padding
    if (key == 2) {  // SENSOR_KEY
      pos++;
      uint32_t raw = 0;
      for (int i = 0; i < 4; i++) raw |= (uint32_t) pkt[pos++] << (8 * i);
      uint8_t il = pkt[pos++];
      std::string id((const char *) pkt.data() + pos, il);
      pos += il;
      float f; memcpy(&f, &raw, 4);
      out.sensors.push_back({id, f});
    } else if (key == 3) {  // BINARY_SENSOR_KEY
      pos++;
      bool v = pkt[pos++] != 0;
      uint8_t il = pkt[pos++];
      std::string id((const char *) pkt.data() + pos, il);
      pos += il;
      out.bsensors.push_back({id, v});
    } else { assert(false && "unknown key"); }
  }
  return out;
}

// Independent ENCODER, written from ESPHome's packet_transport.cpp: build a packet by hand and HDLC it.
static std::vector<uint8_t> encode_ref(const std::string &from, const RefPacket &p) {
  std::vector<uint8_t> buf;
  buf.push_back(0x53); buf.push_back(0x45);  // MAGIC_NUMBER 0x4553 LE
  buf.push_back((uint8_t) from.size());
  for (char c : from) buf.push_back((uint8_t) c);
  while (buf.size() & 3) buf.push_back(0);
  buf.push_back(1);  // DATA_KEY
  for (auto &s : p.sensors) {
    buf.push_back(2);
    float f = s.second; uint32_t raw; memcpy(&raw, &f, 4);
    for (int i = 0; i < 4; i++) buf.push_back((raw >> (8 * i)) & 0xFF);
    buf.push_back((uint8_t) s.first.size());
    for (char c : s.first) buf.push_back((uint8_t) c);
  }
  for (auto &b : p.bsensors) {
    buf.push_back(3);
    buf.push_back(b.second ? 1 : 0);
    buf.push_back((uint8_t) b.first.size());
    for (char c : b.first) buf.push_back((uint8_t) c);
  }
  while (buf.size() & 3) buf.push_back(0);
  uint16_t crc = crc16_ref(buf.data(), buf.size());
  buf.push_back(crc & 0xFF); buf.push_back(crc >> 8);
  std::vector<uint8_t> wire;
  wire.push_back(0x7E);
  for (uint8_t b : buf) {
    if (b == 0x7E || b == 0x7D) { wire.push_back(0x7D); wire.push_back(b ^ 0x20); }
    else wire.push_back(b);
  }
  wire.push_back(0x7E);
  return wire;
}

int main() {
  App.name = "alarmo-display";

  // --- board A: the display, with out commands and in states ---
  UartLinkTransport a;
  a.setup();
  a.set_peer("kc868-aio");
  sensor::Sensor temp; temp.object_id = "room_temp"; temp.state = 21.5f;
  binary_sensor::BinarySensor cmd_disarm; cmd_disarm.object_id = "cmd_disarm_bs";
  binary_sensor::BinarySensor rx_smoke; rx_smoke.object_id = "rx_smoke";
  binary_sensor::BinarySensor rx_siren; rx_siren.object_id = "rx_siren";
  sensor::Sensor rx_battery; rx_battery.object_id = "rx_battery";
  a.add_out_sensor("room_temp", &temp);
  a.add_out_binary_sensor("cmd_disarm", &cmd_disarm);
  a.add_in_binary_sensor("smoke_state", &rx_smoke);
  a.add_in_binary_sensor("siren_state", &rx_siren);
  a.add_in_sensor("battery", &rx_battery);

  // A change fires a packet: cmd_disarm on.
  cmd_disarm.fire(true);
  a.loop();
  assert(!a.tx.empty());
  assert(a.tx_count() == 1);

  // Decode the wire with the independent decoder.
  auto packets = unhdlc(a.tx);
  assert(packets.size() == 1);
  RefPacket ra = decode_ref(packets[0]);
  assert(ra.from == "alarmo-display");
  assert(ra.bsensors.size() == 1 && ra.bsensors[0].first == "cmd_disarm" && ra.bsensors[0].second == true);
  assert(ra.sensors.size() == 1 && ra.sensors[0].first == "room_temp" && fabs(ra.sensors[0].second - 21.5f) < 1e-6);
  printf("A->wire encode: OK (name, sensor float, binary sensor)\n");

  // Full state (15 s resend) carries everything: rewind the clock far enough for the 15 s interval.
  a.tx.clear();
  for (int i = 0; i < 2000; i++) a.loop();  // millis() advances 10 ms per call
  assert(a.tx_count() >= 2);
  packets = unhdlc(a.tx);
  RefPacket ra2 = decode_ref(packets.back());
  assert(ra2.sensors.size() == 1 && ra2.bsensors.size() == 1);
  printf("A full-state resend: OK\n");

  // --- board B (kc868-aio) sends to A, encoded by the independent encoder ---
  RefPacket b;
  b.sensors.push_back({"battery", 87.0f});
  b.bsensors.push_back({"smoke_state", true});
  b.bsensors.push_back({"siren_state", false});
  b.bsensors.push_back({"unknown_thing", true});  // not registered on A: must be ignored
  std::vector<uint8_t> wire_b = encode_ref("kc868-aio", b);
  a.rx = wire_b;
  int packets_seen = 0;
  a.set_on_packet([&] { packets_seen++; });
  a.loop();
  assert(packets_seen == 1);
  assert(a.rx_count() == 1);
  assert(rx_smoke.state == true && rx_smoke.has_state);
  assert(rx_siren.state == false && rx_siren.has_state);
  assert(fabs(rx_battery.state - 87.0f) < 1e-6 && rx_battery.has_state);
  printf("B->A decode: OK (sensor, binary sensors, unknown id ignored)\n");

  // --- peer filter: a packet from another node on the bus is dropped ---
  RefPacket c; c.bsensors.push_back({"smoke_state", false});
  std::vector<uint8_t> wire_c = encode_ref("someone-else", c);
  a.rx = wire_c; a.rx_pos = 0;
  uint32_t rx_before = a.rx_count();
  a.loop();
  assert(a.rx_count() == rx_before);  // not counted
  assert(rx_smoke.state == true);      // unchanged
  printf("peer filter: OK\n");

  // --- own name is ignored (bus echo) ---
  std::vector<uint8_t> wire_self = encode_ref("alarmo-display", b);
  a.rx = wire_self; a.rx_pos = 0;
  a.loop();
  assert(a.rx_count() == rx_before);
  printf("own-name filter: OK\n");

  // --- corrupt CRC is dropped ---
  std::vector<uint8_t> wire_bad = encode_ref("kc868-aio", b);
  wire_bad[5] ^= 0xFF;  // flip a byte inside the frame
  a.rx = wire_bad; a.rx_pos = 0;
  a.loop();
  assert(a.rx_count() == rx_before);
  printf("CRC check: OK\n");

  // --- escaping: an id that contains 0x7E and 0x7D survives the round trip ---
  App.name = "esc-test";
  UartLinkTransport e;
  e.setup();
  binary_sensor::BinarySensor weird; weird.object_id = "x";
  { std::string wid("a\x7E" "b\x7D" "c"); e.add_out_binary_sensor(wid.c_str(), &weird); }
  weird.fire(true);
  e.loop();
  e.tx.clear();  // drop the registration's initial packet
  weird.fire(false);  // a change -> exactly one packet
  e.loop();
  auto ep = unhdlc(e.tx);
  assert(ep.size() == 1);
  RefPacket re = decode_ref(ep[0]);
  assert(re.bsensors.size() == 1 && re.bsensors[0].first == std::string("a\x7E" "b\x7D" "c"));
  printf("HDLC escaping: OK\n");

  // --- disabled link: no rx, no tx ---
  a.set_enabled(false);
  a.rx = encode_ref("kc868-aio", b); a.rx_pos = 0;
  cmd_disarm.fire(false);
  size_t tx_before = a.tx.size();
  a.loop();
  assert(a.rx_count() == rx_before);
  assert(a.tx.size() == tx_before);
  printf("pause: OK\n");

  printf("ALL TESTS PASSED\n");
  return 0;
}
