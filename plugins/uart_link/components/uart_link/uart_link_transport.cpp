#include "uart_link_transport.h"

#include <cstring>

#include "esphome/core/application.h"
#include "esphome/core/log.h"

namespace esphome::uart_link {

// The keys of the packet's state section, as ESPHome's packet_transport writes them.
static const uint8_t KEY_DATA = 1;
static const uint8_t KEY_SENSOR = 2;
static const uint8_t KEY_BINARY_SENSOR = 3;
static const uint16_t MAGIC_NUMBER = 0x4553;

static size_t round4(size_t value) { return (value + 3) & ~3; }

// The CRC-16 of ESPHome's UART transport: CCITT (polynomial 0x1021, initial value 0), low byte first on the wire.
static uint16_t crc16(const uint8_t *data, size_t len) {
  uint16_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (int bit = 0; bit < 8; bit++)
      crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021) : static_cast<uint16_t>(crc << 1);
  }
  return crc;
}

// A little-endian reader over the packet's state section.
class Reader {
 public:
  Reader(const uint8_t *data, size_t len) : data_(data), len_(len) {}
  bool get_u8(uint8_t &out) {
    if (pos_ + 1 > len_) return false;
    out = data_[pos_++];
    return true;
  }
  bool get_u32(uint32_t &out) {
    if (pos_ + 4 > len_) return false;
    out = 0;
    for (int i = 0; i < 4; i++) out |= static_cast<uint32_t>(data_[pos_++]) << (8 * i);
    return true;
  }
  // An id: a length byte and the bytes. Returns false when the packet ends here (the zero padding).
  bool get_id(std::string &out) {
    uint8_t len;
    if (!get_u8(len) || len == 0 || pos_ + len > len_) return false;
    out.assign(reinterpret_cast<const char *>(data_ + pos_), len);
    pos_ += len;
    return true;
  }
  size_t left() const { return len_ - pos_; }

 private:
  const uint8_t *data_;
  size_t len_, pos_{0};
};

static void add_u16(std::vector<uint8_t> &vec, uint16_t data) {
  vec.push_back(static_cast<uint8_t>(data));
  vec.push_back(static_cast<uint8_t>(data >> 8));
}

static void add_u32(std::vector<uint8_t> &vec, uint32_t data) {
  vec.push_back(data & 0xFF);
  vec.push_back((data >> 8) & 0xFF);
  vec.push_back((data >> 16) & 0xFF);
  vec.push_back((data >> 24) & 0xFF);
}

static void add_id(std::vector<uint8_t> &vec, const char *id) {
  auto len = strlen(id);
  vec.push_back(static_cast<uint8_t>(len));
  for (size_t i = 0; i < len; i++)
    vec.push_back(static_cast<uint8_t>(id[i]));
}

void UartLinkTransport::add_out_sensor(const char *broadcast_id, sensor::Sensor *sensor) {
  const char *id = broadcast_id[0] != '\0' ? broadcast_id : sensor->get_object_id().c_str();
  out_sensors_.push_back({sensor, id, true});
  sensor->add_on_state_callback([this, sensor](float) {
    for (auto &out : this->out_sensors_)
      if (out.sensor == sensor)
        out.updated = true;
    this->updated_ = true;
  });
}

void UartLinkTransport::add_out_binary_sensor(const char *broadcast_id, binary_sensor::BinarySensor *sensor) {
  const char *id = broadcast_id[0] != '\0' ? broadcast_id : sensor->get_object_id().c_str();
  out_binary_sensors_.push_back({sensor, id, true});
  sensor->add_on_state_callback([this, sensor](bool) {
    for (auto &out : this->out_binary_sensors_)
      if (out.sensor == sensor)
        out.updated = true;
    this->updated_ = true;
  });
}

// The room a record still needs in the packet, the same rounding ESPHome's flush_ applies to the whole buffer.
size_t UartLinkTransport::room_left_() const {
  return LINK_MAX_PACKET - round4(this->data_.size());
}

void UartLinkTransport::add_data_(uint8_t key, const char *id, uint32_t data) {
  auto len = 1 + 4 + 1 + strlen(id);
  if (this->room_left_() < round4(len)) {
    this->send_packet_(this->data_);
    this->data_ = this->header_;
    this->data_.push_back(KEY_DATA);
  }
  this->data_.push_back(key);
  add_u32(this->data_, data);
  add_id(this->data_, id);
}

void UartLinkTransport::add_binary_data_(const char *id, bool data) {
  auto len = 1 + 1 + 1 + strlen(id);
  if (this->room_left_() < round4(len)) {
    this->send_packet_(this->data_);
    this->data_ = this->header_;
    this->data_.push_back(KEY_DATA);
  }
  this->data_.push_back(KEY_BINARY_SENSOR);
  this->data_.push_back(data ? 1 : 0);
  add_id(this->data_, id);
}

void UartLinkTransport::send_states_(bool all) {
  if (!this->enabled_)
    return;
  // The header is invariant: magic, this node's name, padded to four bytes.
  this->data_ = this->header_;
  this->data_.push_back(KEY_DATA);
  for (auto &out : this->out_sensors_) {
    if (all || out.updated) {
      out.updated = false;
      union {
        uint32_t u32;
        float f32;
      } value{.f32 = out.sensor->get_state()};
      this->add_data_(KEY_SENSOR, out.id, value.u32);
    }
  }
  for (auto &out : this->out_binary_sensors_) {
    if (all || out.updated) {
      out.updated = false;
      this->add_binary_data_(out.id, out.sensor->state);
    }
  }
  // The packet is padded to a four byte boundary as a whole (ESPHome's flush_ rounds header and data together).
  while (this->data_.size() & 0x3)
    this->data_.push_back(0);
  this->send_packet_(this->data_);
  this->updated_ = false;
}

void UartLinkTransport::write_byte_(uint8_t byte) {
  if (byte == LINK_FLAG_BYTE || byte == LINK_CONTROL_BYTE) {
    this->write_byte(LINK_CONTROL_BYTE);
    byte ^= 0x20;
  }
  this->write_byte(byte);
}

void UartLinkTransport::send_packet_(const std::vector<uint8_t> &buf) {
  if (!this->enabled_ || buf.empty())
    return;
  this->write_byte(LINK_FLAG_BYTE);
  for (uint8_t byte : buf)
    this->write_byte_(byte);
  auto crc = crc16(buf.data(), buf.size());
  this->write_byte_(crc & 0xFF);
  this->write_byte_(crc >> 8);
  this->write_byte(LINK_FLAG_BYTE);
  this->tx_count_++;
}

void UartLinkTransport::process_(const std::vector<uint8_t> &data) {
  // Magic and the sender's name, in clear text; the states follow, encrypted on ESPHome's side when a key is set (this
  // link sends and reads them in clear text, as ESPHome's UART transport does without an encryption key).
  if (data.size() < 4)
    return;
  uint16_t magic = data[0] | (data[1] << 8);
  if (magic != MAGIC_NUMBER)
    return;
  size_t name_len = data[2];
  if (name_len == 0 || 3 + name_len > data.size())
    return;
  std::string sender(reinterpret_cast<const char *>(data.data() + 3), name_len);
  if (sender == this->name_)
    return;  // our own packet, back from a bus that echoes
  if (!this->peer_.empty() && sender != this->peer_)
    return;  // another node on a multi-drop bus
  this->rx_count_++;
  this->last_rx_ms_ = millis();
  this->dispatch_(data);
  if (this->on_packet_)
    this->on_packet_();
}

// The state section of a packet, as ESPHome's packet_transport writes it: a data key (or a rolling code key, which this
// link does not use), then records of a sensor key with a float and an id, or a binary sensor key with a byte and an
// id, padded with zeros. Every record the screen registered under that remote id is published.
void UartLinkTransport::dispatch_(const std::vector<uint8_t> &data) {
  // Skip the header: magic, the sender's name, padded to a four byte boundary.
  if (data.size() < 4) return;
  size_t name_len = data[2];
  size_t pos = round4(3 + name_len);
  if (pos >= data.size()) return;
  Reader reader(data.data() + pos, data.size() - pos);
  uint8_t key;
  if (!reader.get_u8(key) || key != KEY_DATA) return;  // no rolling code on this link
  while (reader.left() > 0) {
    if (!reader.get_u8(key)) return;
    if (key == 0) continue;  // the padding
    if (key == KEY_SENSOR) {
      uint32_t raw;
      std::string id;
      if (!reader.get_u32(raw) || !reader.get_id(id)) return;
      union { uint32_t u32; float f32; } value{.u32 = raw};
      for (const auto &in : in_sensors_)
        if (in.id == id)
          static_cast<sensor::Sensor *>(in.entity)->publish_state(value.f32);
    } else if (key == KEY_BINARY_SENSOR) {
      uint8_t raw;
      std::string id;
      if (!reader.get_u8(raw) || !reader.get_id(id)) return;
      for (const auto &in : in_binary_sensors_)
        if (in.id == id)
          static_cast<binary_sensor::BinarySensor *>(in.entity)->publish_state(raw != 0);
    } else {
      return;  // a key this link does not know: stop, the packet is not its own
    }
  }
}

void UartLinkTransport::setup() {
  // The header is invariant: magic, this node's name, padded to four bytes. Built once; App's name is final by now.
  if (!this->header_.empty())
    return;
  this->name_ = App.get_name();
  add_u16(this->header_, MAGIC_NUMBER);
  add_id(this->header_, this->name_.c_str());
  while (this->header_.size() & 0x3)
    this->header_.push_back(0);
}

void UartLinkTransport::loop() {
  if (this->updated_)
    this->send_states_(false);
  // Every 15 seconds the full state, so a peer that restarted catches up (ESPHome's own update_interval default).
  if (this->enabled_ && this->out_sensors_.size() + this->out_binary_sensors_.size() > 0 &&
      millis() - this->last_send_ms_ >= 15000) {
    this->last_send_ms_ = millis();
    this->send_states_(true);
  }
  if (!this->enabled_)
    return;
  while (this->available()) {
    uint8_t byte;
    if (!this->read_byte(&byte))
      return;
    if (byte == LINK_FLAG_BYTE) {
      if (this->rx_started_ && this->receive_buffer_.size() > 6) {
        auto len = this->receive_buffer_.size();
        auto crc = crc16(this->receive_buffer_.data(), len - 2);
        if (crc == (this->receive_buffer_[len - 2] | (this->receive_buffer_[len - 1] << 8))) {
          this->receive_buffer_.resize(len - 2);
          this->process_(this->receive_buffer_);
        }
      }
      this->rx_started_ = true;
      this->rx_control_ = false;
      this->receive_buffer_.clear();
      continue;
    }
    if (!this->rx_started_)
      continue;
    if (byte == LINK_CONTROL_BYTE) {
      this->rx_control_ = true;
      continue;
    }
    if (this->rx_control_) {
      byte ^= 0x20;
      this->rx_control_ = false;
    }
    if (this->receive_buffer_.size() == LINK_MAX_PACKET) {
      this->rx_started_ = false;
      this->receive_buffer_.clear();
      continue;
    }
    this->receive_buffer_.push_back(byte);
  }
}

}  // namespace esphome::uart_link
