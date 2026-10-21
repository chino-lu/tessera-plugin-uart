#include "uart_link.h"

#include "esphome/core/hal.h"

#include <cstdio>
#include <string>

namespace esphome::uart_link {

using tessera::Font;
namespace ui = tessera::ui;

// The tile: the link's health on a page. A dot that says the peer was heard (a tone), the time of the last packet, and
// the two counters. create() makes the parts once; on_tick() sets their texts, and ui::set_text changes a label only
// when its text differs.
class LinkTile : public tessera::Tile {
 public:
  explicit LinkTile(const tessera::Plugin *plugin) : plugin_(plugin) {}

  void create(const tessera::TileContext &c) override {
    width_ = c.width;
    height_ = c.height;
    name_ = c.options["peer"] | "";
    dot_ = ui::block(c.parent, theme::MUTED);
    lv_obj_set_size(dot_, ui::px(10), ui::px(10));
    lv_obj_set_style_radius(dot_, LV_RADIUS_CIRCLE, 0);
    title_ = ui::label(c.parent, Font::BODY, theme::INK);
    lv_obj_set_width(title_, width_ - ui::px(18));
    last_ = ui::label(c.parent, Font::BODY, theme::MUTED);
    lv_obj_set_width(last_, width_ - ui::px(18));
    counts_ = ui::label(c.parent, Font::BODY, theme::MUTED);
    lv_obj_set_width(counts_, width_ - ui::px(18));
  }

  void on_tick(uint32_t epoch) override {
    const UartLink *link = link_;
    const bool heard = link != nullptr && link->transport_last_rx_ms() != 0;
    ui::set_fill(dot_, heard ? tessera::Tone::GOOD : tessera::Tone::BUSY, theme::MUTED);
    std::string title = name_.empty() ? plugin_->text("any_peer") : name_;
    std::string last, counts;
    if (link == nullptr) {
      last = plugin_->text("waiting");
    } else if (!heard) {
      last = plugin_->text("no_packet");
    } else {
      last = tessera::fill(plugin_->text("last_packet"), "when", ago_text(link->transport_last_rx_ms()));
    }
    if (link != nullptr) {
      char buf[96];
      snprintf(buf, sizeof(buf), plugin_->text("counts"), (unsigned) link->transport_rx_count(),
               (unsigned) link->transport_tx_count());
      counts = buf;
    }
    ui::set_text(title_, title);
    ui::set_text(last_, last);
    ui::set_text(counts_, counts);
    const int dh = ui::line_height(Font::BODY);
    const int top = (height_ - 3 * dh - ui::px(8)) / 2;
    lv_obj_set_pos(dot_, 0, top + dh / 2 - ui::px(5));
    lv_obj_set_pos(title_, ui::px(18), top);
    lv_obj_set_height(title_, dh);
    lv_obj_set_pos(last_, ui::px(18), top + dh + ui::px(4));
    lv_obj_set_height(last_, dh);
    lv_obj_set_pos(counts_, ui::px(18), top + 2 * (dh + ui::px(4)));
    lv_obj_set_height(counts_, dh);
  }

  // Light and dark: the theme roles have other values now.
  void on_theme() override {
    ui::set_color(title_, theme::INK);
    ui::set_color(last_, theme::MUTED);
    ui::set_color(counts_, theme::MUTED);
    const bool heard = link_ != nullptr && link_->transport_last_rx_ms() != 0;
    ui::set_fill(dot_, heard ? tessera::Tone::GOOD : tessera::Tone::BUSY, theme::MUTED);
  }

  // The tile is bound to the plugin's component, which owns the transport.
  void set_link(const UartLink *link) { link_ = link; }

 private:
  // "5 s ago", "3 min ago" from the millis() of the last packet, in the screen's words.
  std::string ago_text(uint32_t then_ms) const {
    const uint32_t age = (millis() - then_ms) / 1000;
    char buf[48];
    if (age < 60) {
      snprintf(buf, sizeof(buf), plugin_->text("seconds_ago"), (unsigned) age);
    } else if (age < 3600) {
      snprintf(buf, sizeof(buf), plugin_->text("minutes_ago"), (unsigned) (age / 60));
    } else {
      snprintf(buf, sizeof(buf), plugin_->text("hours_ago"), (unsigned) (age / 3600));
    }
    return buf;
  }

  const tessera::Plugin *plugin_;
  const UartLink *link_{nullptr};
  tessera::Text name_;
  int width_ = 0, height_ = 0;
  lv_obj_t *dot_{}, *title_{}, *last_{}, *counts_{};
};

const char *UartLink::state_() const {
  if (on_ != nullptr && !on_->state)
    return "status_off";
  return transport_.last_rx_ms() != 0 ? "status_on" : "status_waiting";
}

void UartLink::publish_() {
  const char *state = state_();
  if (state == published_ || status_ == nullptr)
    return;
  published_ = state;
  status_->publish_state(text(state));
}

void UartLink::setup() {
  transport_.set_on_packet([this] { this->publish_(); });
  add_tile("link", [this]() {
    auto *tile = new LinkTile(this);
    tile->set_link(this);
    return tile;
  });
}

void UartLink::loop() {
  const bool on = on_ == nullptr || on_->state;
  transport_.set_enabled(on);
  transport_.loop();
}

void UartLink::on_ready() { publish_(); }

void UartLink::on_interval(uint32_t now_ms) {
  if (now_ms - last_ms_ < 1000)
    return;
  last_ms_ = now_ms;
  publish_();
  if (rx_count_ != nullptr && transport_.rx_count() != last_rx_count_) {
    last_rx_count_ = transport_.rx_count();
    rx_count_->publish_state(last_rx_count_);
  }
  if (tx_count_ != nullptr && transport_.tx_count() != last_tx_count_) {
    last_tx_count_ = transport_.tx_count();
    tx_count_->publish_state(last_tx_count_);
  }
}

bool UartLink::settings(tessera::SettingsPage &page) {
  page.icon = "\U000F065C";  // serial-port
  if (on_ != nullptr) {
    switch_::Switch *on = on_;
    page.toggle(text("on"), [on] { return on->state; },
              [on](bool value) { value ? on->turn_on() : on->turn_off(); });
  }
  page.info(text("status"), [this] { return std::string(text(state_())); });
  return true;
}

}  // namespace esphome::uart_link
