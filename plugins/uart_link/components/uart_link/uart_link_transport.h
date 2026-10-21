#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/uart/uart.h"

namespace esphome::uart_link {

// The wire protocol of ESPHome's packet transport over a UART (the `packet_transport` platform, `platform: uart`):
// a data packet is a 16-bit magic (0x4553), the sending node's name (a length byte and the name), padded to a four byte
// boundary, then the states: a data key byte, then per sensor a sensor key, a float and the id, and per binary sensor a
// binary sensor key, a byte and the id, all little-endian and padded to a four byte boundary. The packet is wrapped as
// asynchronous HDLC: flag byte 0x7E at both ends, a CRC-16 (CCITT, little-endian) over the packet before the flags,
// and any flag or escape byte in the packet escaped as 0x7D followed by the byte XOR 0x20. A Tessera screen and any
// other ESPHome node exchange states over the serial line with this, RS485 multi-drop included.
//
// The framing needs no timer: a packet ends at its closing flag, and the loop reads whatever arrived.
static const uint16_t LINK_MAX_PACKET = 508;
static const uint8_t LINK_FLAG_BYTE = 0x7E;
static const uint8_t LINK_CONTROL_BYTE = 0x7D;

class UartLinkTransport : public uart::UARTDevice {
 public:
  void setup() override;
  void loop();
  float get_setup_priority() const override { return setup_priority::PROCESSOR; }

  // The other node's ESPHome name: only its packets are read. Empty: every node but this one is read.
  void set_peer(const std::string &peer) { peer_ = peer; }
  // Whether the link is on: off stops the reading and the sending.
  void set_enabled(bool enabled) { enabled_ = enabled; }
  // Called for every packet that passed the peer's name and the CRC.
  void set_on_packet(std::function<void()> on_packet) { on_packet_ = std::move(on_packet); }

  // This screen's own states, sent to the peer. The broadcast id is the id the peer receives; empty is the entity's id.
  void add_out_sensor(const char *broadcast_id, sensor::Sensor *sensor);
  void add_out_binary_sensor(const char *broadcast_id, binary_sensor::BinarySensor *sensor);
  // The peer's states, received into this screen's entities: the entity to publish, by the id the peer sends
  // (the remote id). Several entities may share one remote id (a sensor and a binary sensor of the same name).
  void add_in_sensor(const char *remote_id, sensor::Sensor *sensor) {
    in_sensors_.emplace_back(remote_id, sensor);
  }
  void add_in_binary_sensor(const char *remote_id, binary_sensor::BinarySensor *sensor) {
    in_binary_sensors_.emplace_back(remote_id, sensor);
  }

  uint32_t rx_count() const { return rx_count_; }
  uint32_t tx_count() const { return tx_count_; }
  // The millis() of the last good packet of the peer, 0 while none arrived.
  uint32_t last_rx_ms() const { return last_rx_ms_; }

 protected:
  void send_packet_(const std::vector<uint8_t> &buf);
  void write_byte_(uint8_t byte);
  void process_(const std::vector<uint8_t> &data);
  void send_states_(bool all);
  void add_data_(uint8_t key, const char *id, uint32_t data);
  void add_binary_data_(const char *id, bool data);
  void dispatch_(const std::vector<uint8_t> &data);
  size_t room_left_() const;

  struct OutSensor {
    sensor::Sensor *sensor;
    const char *id;
    bool updated;
  };
  struct OutBinarySensor {
    binary_sensor::BinarySensor *sensor;
    const char *id;
    bool updated;
  };
  struct InEntity {
    InEntity(const char *id, void *entity) : id(id), entity(entity) {}
    std::string id;
    void *entity;
  };

  std::string peer_;
  std::string name_;
  std::vector<uint8_t> header_;
  std::vector<uint8_t> data_;
  std::vector<uint8_t> receive_buffer_;
  std::vector<OutSensor> out_sensors_;
  std::vector<OutBinarySensor> out_binary_sensors_;
  std::vector<InEntity> in_sensors_;
  std::vector<InEntity> in_binary_sensors_;
  std::function<void()> on_packet_;
  bool enabled_{true};
  bool rx_started_{};
  bool rx_control_{};
  bool updated_{};
  uint32_t rx_count_{};
  uint32_t tx_count_{};
  uint32_t last_rx_ms_{};
  uint32_t last_send_ms_{};
};

}  // namespace esphome::uart_link
