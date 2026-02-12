DOMAIN = "hcc"

CONF_ADDRESS = "address_string"
CONF_UPDATE_MINUTES = "update_minutes"
CONF_API_URL = "api_url"

DEFAULT_UPDATE_MINUTES = 60
MIN_UPDATE_MINUTES = 5
MAX_UPDATE_MINUTES = 1440

API_BASE = "https://api.hcc.govt.nz/FightTheLandFill/get_Collection_Dates"

# Status text constants
STATUS_SUCCESS = "success"
STATUS_NETWORK = "network_error"
STATUS_JSON = "json_parsing"
STATUS_UNEXPECTED = "unexpected_error"

# Added "button" to the list
PLATFORMS = ["sensor", "binary_sensor", "number", "button", "switch"]