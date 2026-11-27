"""Constants for VerbrauchsMonitor."""
from typing import Final

DOMAIN: Final = "verbrauchsmonitor"
PLATFORMS: Final = ["sensor"]

CONF_METER_NAME: Final = "meter_name"
CONF_METER_NUMBER: Final = "meter_number"
CONF_CONSUMPTION_ENTITY: Final = "consumption_entity"
CONF_CONSUMPTION_POWER_ENTITY: Final = "consumption_power_entity"
CONF_FEED_IN_ENTITY: Final = "feed_in_entity"
CONF_FEED_IN_POWER_ENTITY: Final = "feed_in_power_entity"
CONF_OUTDOOR_ILLUMINANCE_ENTITY: Final = "outdoor_illuminance_entity"
CONF_OUTDOOR_TEMPERATURE_ENTITY: Final = "outdoor_temperature_entity"
CONF_OUTDOOR_WIND_DIRECTION_ENTITY: Final = "outdoor_wind_direction_entity"
CONF_DAILY_PRECIPITATION_ENTITY: Final = "daily_precipitation_entity"
CONF_OUTDOOR_HUMIDITY_ENTITY: Final = "outdoor_humidity_entity"

# Contract and tariff configuration. Prices are stored as net values;
# gross values are calculated from the configured VAT rate.
CONF_CONTRACT_NAME: Final = "contract_name"
CONF_CONTRACT_NUMBER: Final = "contract_number"
CONF_CONTRACT_START: Final = "contract_start"
CONF_CONTRACT_END: Final = "contract_end"
CONF_PURCHASE_PRICE_NET: Final = "purchase_price_net"
CONF_FEED_IN_PRICE_NET: Final = "feed_in_price_net"
CONF_VAT_RATE: Final = "vat_rate"
CONF_BASE_PRICE_NET: Final = "base_price_net"
CONF_BASE_PRICE_PERIOD: Final = "base_price_period"
CONF_MONTHLY_ADVANCE: Final = "monthly_advance"
CONF_BILLING_START: Final = "billing_start"
CONF_BILLING_END: Final = "billing_end"

CARD_URL: Final = "/verbrauchsmonitor/verbrauchsmonitor-card.js"
CARD_FILENAME: Final = "verbrauchsmonitor-card.js"
RELEASE_VERSION: Final = "0.0.1"
RELEASE_STAGE: Final = "Prod"
RELEASE_REVISION: Final = "R0171"
INTEGRATION_VERSION: Final = "0.0.1"

ROLE_CONFIG: Final = {
    CONF_CONSUMPTION_ENTITY: ("consumption_counter", "Verbrauch Zählerstand", "mdi:counter"),
    CONF_CONSUMPTION_POWER_ENTITY: ("consumption_power", "Verbrauch Leistung", "mdi:flash"),
    CONF_FEED_IN_ENTITY: ("feed_in_counter", "Einspeisung Zählerstand", "mdi:counter"),
    CONF_FEED_IN_POWER_ENTITY: ("feed_in_power", "Einspeisung Leistung", "mdi:solar-power"),
}
