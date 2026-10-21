#pragma once
#include <string>
namespace esphome {
class Application {
 public:
  std::string name;
  std::string get_name() { return name; }
};
extern Application App;
}  // namespace esphome
