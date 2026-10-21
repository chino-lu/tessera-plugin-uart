"""UART link entities: the entities a screen's UART link sends to and receives from the peer board.

This component holds no code of its own: it registers the entities of the screen's Override YAML with the uart_link
component (uart_link:), which runs the transport. It exists so a screen's Override YAML can configure the link's
entities beside the hub:

    uart_link_entities:
      link: uart_link
      out_sensors:
        - id: my_sensor
          broadcast_id: room_temp
      in_binary_sensors:
        - id: rx_smoke
          remote_id: smoke_state
"""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor, sensor
from esphome.const import CONF_ID

DEPENDENCIES = ["uart_link"]

CONF_LINK = "link"
CONF_OUT_SENSORS = "out_sensors"
CONF_OUT_BINARY_SENSORS = "out_binary_sensors"
CONF_IN_SENSORS = "in_sensors"
CONF_IN_BINARY_SENSORS = "in_binary_sensors"

uart_link_ns = cg.esphome_ns.namespace("uart_link")
UartLink = uart_link_ns.class_("UartLink", cg.Component)

entities_ns = cg.esphome_ns.namespace("uart_link_entities")
UartLinkEntities = entities_ns.class_("UartLinkEntities", cg.Component)

_OUT_SENSOR = cv.Schema(
    {
        cv.Required(CONF_ID): cv.use_id(sensor.Sensor),
        cv.Optional("broadcast_id"): cv.validate_id_name,
    }
)
_OUT_BINARY_SENSOR = cv.Schema(
    {
        cv.Required(CONF_ID): cv.use_id(binary_sensor.BinarySensor),
        cv.Optional("broadcast_id"): cv.validate_id_name,
    }
)
_IN_SENSOR = cv.Schema(
    {
        cv.Required(CONF_ID): cv.use_id(sensor.Sensor),
        cv.Optional("remote_id"): cv.string_strict,
    }
)
_IN_BINARY_SENSOR = cv.Schema(
    {
        cv.Required(CONF_ID): cv.use_id(binary_sensor.BinarySensor),
        cv.Optional("remote_id"): cv.string_strict,
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(UartLinkEntities),
        cv.Required(CONF_LINK): cv.use_id(UartLink),
        cv.Optional(CONF_OUT_SENSORS, default=[]): cv.ensure_list(_OUT_SENSOR),
        cv.Optional(CONF_OUT_BINARY_SENSORS, default=[]): cv.ensure_list(_OUT_BINARY_SENSOR),
        cv.Optional(CONF_IN_SENSORS, default=[]): cv.ensure_list(_IN_SENSOR),
        cv.Optional(CONF_IN_BINARY_SENSORS, default=[]): cv.ensure_list(_IN_BINARY_SENSOR),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    link = await cg.get_variable(config[CONF_LINK])
    for out in config[CONF_OUT_SENSORS]:
        cg.add(link.add_out_sensor(await cg.get_variable(out[CONF_ID]), out.get("broadcast_id", "")))
    for out in config[CONF_OUT_BINARY_SENSORS]:
        cg.add(link.add_out_binary_sensor(await cg.get_variable(out[CONF_ID]), out.get("broadcast_id", "")))
    for incoming in config[CONF_IN_SENSORS]:
        cg.add(link.add_in_sensor(await cg.get_variable(incoming[CONF_ID]), incoming.get("remote_id", "")))
    for incoming in config[CONF_IN_BINARY_SENSORS]:
        cg.add(link.add_in_binary_sensor(await cg.get_variable(incoming[CONF_ID]), incoming.get("remote_id", "")))
