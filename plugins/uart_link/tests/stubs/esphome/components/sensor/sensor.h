#pragma once
#include <functional>
#include <string>
namespace esphome::sensor {
class Sensor {
 public:
  float state = 0;
  bool has_state = false;
  std::string object_id;
  std::string get_object_id() { return object_id; }
  float get_state() { return state; }
  void publish_state(float v) { state = v; has_state = true; }
  void add_on_state_callback(std::function<void(float)> cb) { cb_ = cb; }
  void fire(float v) { state = v; if (cb_) cb_(v); }
 private:
  std::function<void(float)> cb_;
};
}  // namespace esphome::sensor
