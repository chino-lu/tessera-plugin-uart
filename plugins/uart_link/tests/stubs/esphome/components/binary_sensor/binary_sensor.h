#pragma once
#include <functional>
#include <string>
namespace esphome::binary_sensor {
class BinarySensor {
 public:
  bool state = false;
  bool has_state = false;
  std::string object_id;
  std::string get_object_id() { return object_id; }
  void publish_state(bool v) { state = v; has_state = true; }
  void add_on_state_callback(std::function<void(bool)> cb) { cb_ = cb; }
  void fire(bool v) { state = v; if (cb_) cb_(v); }
 private:
  std::function<void(bool)> cb_;
};
}  // namespace esphome::binary_sensor
