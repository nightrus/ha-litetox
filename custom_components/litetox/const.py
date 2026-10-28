"""Constants for Litetox Proxy."""

DOMAIN = "litetox"
VERSION = "0.4.6"
CARD_URL = "/litetox/litetox-card.js"

CONF_IMEI = "imei"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_HEATER_MINUTES = "heater_minutes"
CONF_ALTOX_HOST = "altox_host"
CONF_ALTOX_PORT = "altox_port"

DEFAULT_SCAN_INTERVAL = 15          # seconds
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 600
DEFAULT_HEATER_MINUTES = 0          # 0 = module default (TIME1)
# ALTOX SERVER 2.0 the proxy mirrors the module session to (empty host = mirror off)
DEFAULT_ALTOX_HOST = "d2.altox.app"
DEFAULT_ALTOX_PORT = 20332

# after a command, poll the command status this often until the module answers
COMMAND_POLL = 3
COMMAND_TIMEOUT = 90

SERVICE_SEND_COMMAND = "send_command"
SERVICE_START_HEATER = "start_heater"
ATTR_COMMAND = "command"
ATTR_MINUTES = "minutes"
ATTR_DEVICE_ID = "device_id"
