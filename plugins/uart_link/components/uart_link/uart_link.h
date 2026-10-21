#pragma once

#include <string>

#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/smart_display/plugin_api.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "uart_link_transport.h"

namespace esphome::uart_link {

// The plugin: the packet transport link over the screen's UART, and its health on a tile and on the screen's settings
// page. The transport is this folder's UartLinkTransport; the switch, the status text sensor and the two counters are
// template entities of plugin.yaml, which Home Assistant shows as well.
class UartLink : public Component, public tessera::Plugin {
 public:
  void setup() override;
  float get_setup_priority() const override { return setup_priority::LATE; }
  void loop() override;
  void on_ready() override;
  void on_interval(uint32_t now_ms) override;
  bool settings(tessera::SettingsPage &page) override;

  void set_peer(const std::string &peer) { transport_.set_peer(peer); }
  void set_on(switch_::Switch *on) { on_ = on; }
  void set_status(text_sensor::TextSensor *status) { status_ = status; }
  void set_rx_count(sensor::Sensor *rx_count) { rx_count_ = rx_count; }
  void set_tx_count(sensor::Sensor *tx_count) { tx_count_ = tx_count; }
  void add_out_sensor(sensor::Sensor *sensor, const std::string &broadcast_id) {
    transport_.add_out_sensor(broadcast_id.c_str(), sensor);
  }
  void add_out_binary_sensor(binary_sensor::BinarySensor *sensor, const std::string &broadcast_id) {
    transport_.add_out_binary_sensor(broadcast_id.c_str(), sensor);
  }

  // What the tile reads: the transport's own counters and the time of the last packet of the peer.
  uint32_t transport_rx_count() const { return transport_.rx_count(); }
  uint32_t transport_tx_count() const { return transport_.tx_count(); }
  uint32_t transport_last_rx_ms() const { return transport_.last_rx_ms(); }

 protected:
  // The key of the screen's text for what the link does now: status_on, status_off or status_waiting.
  const char *state_() const;
  void publish_();

  UartLinkTransport transport_;
  switch_::Switch *on_{nullptr};
  text_sensor::TextSensor *status_{nullptr};
  sensor::Sensor *rx_count_{nullptr};
  sensor::Sensor *tx_count_{nullptr};
  const char *published_{nullptr};
  uint32_t last_ms_{0};
  uint32_t last_rx_count_{0};
  uint32_t last_tx_count_{0};
};

}  // namespace esphome::uart_link
