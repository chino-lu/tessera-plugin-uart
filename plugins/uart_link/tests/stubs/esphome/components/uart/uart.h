#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
namespace esphome {
namespace setup_priority { constexpr float PROCESSOR = 250.0f; }
class Component {
 public:
  virtual void setup() {}
  virtual float get_setup_priority() const { return 0; }
  virtual ~Component() = default;
};
namespace uart {
struct UARTComponent {};
class UARTDevice : public Component {
 public:
  void write_byte(uint8_t data) { tx.push_back(data); }
  bool read_byte(uint8_t *data) {
    if (rx_pos >= rx.size()) return false;
    *data = rx[rx_pos++];
    return true;
  }
  size_t available() { return rx.size() - rx_pos; }
  std::vector<uint8_t> tx, rx;
  size_t rx_pos = 0;
};
}  // namespace uart
}  // namespace esphome
