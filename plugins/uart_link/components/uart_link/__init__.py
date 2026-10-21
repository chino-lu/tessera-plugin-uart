"""UART link: ESPHome's packet transport over a UART on the screen's free pins.

The transport itself is this folder's uart_link_transport.h/.cpp: the packet_transport wire format (magic, the node's
name, the sensor and binary sensor states) framed as asynchronous HDLC (flag byte 0x7E, escape 0x7D, CRC-16), the very
protocol of ESPHome's packet_transport platform (platform: uart), so a Tessera screen and any other ESPHome node
exchange states over a serial link, RS485 included. This component is the plugin of it: it owns the switch, the status
text sensor and the two counters of plugin.yaml, keeps them up, and draws the link's health on a tile and on the screen's
settings page. The entities the link sends and receives are registered by the sibling component uart_link_entities
(same folder of components/), from the screen's Override YAML. register_plugin() takes the id, version, tile memory and
the screen's texts from the manifest and translations/ beside this folder.
"""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor, smart_display, switch, text_sensor, uart
from esphome.const import CONF_ID, CONF_UART_ID

DEPENDENCIES = ["smart_display", "uart", "sensor", "binary_sensor", "switch", "text_sensor"]

CONF_PEER = "peer"
CONF_ON = "on"
CONF_STATUS = "status"
CONF_RX_COUNT = "rx_count"
CONF_TX_COUNT = "tx_count"

uart_link_ns = cg.esphome_ns.namespace("uart_link")
UartLink = uart_link_ns.class_("UartLink", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(UartLink),
        cv.Required(CONF_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Optional(CONF_PEER, default=""): cv.string,
        cv.Required(CONF_ON): cv.use_id(switch.Switch),
        cv.Required(CONF_STATUS): cv.use_id(text_sensor.TextSensor),
        cv.Required(CONF_RX_COUNT): cv.use_id(sensor.Sensor),
        cv.Required(CONF_TX_COUNT): cv.use_id(sensor.Sensor),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await smart_display.register_plugin(var, __file__)
    await uart.register_uart_device(var, config)
    cg.add(var.set_peer(config[CONF_PEER]))
    cg.add(var.set_on(await cg.get_variable(config[CONF_ON])))
    cg.add(var.set_status(await cg.get_variable(config[CONF_STATUS])))
    cg.add(var.set_rx_count(await cg.get_variable(config[CONF_RX_COUNT])))
    cg.add(var.set_tx_count(await cg.get_variable(config[CONF_TX_COUNT])))
