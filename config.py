
# API Configuration
# Get these from https://www.delta.exchange/app/account/manageapikeys
# NOTE: Ensure you are using the correct domain (india vs global)
API_KEY = ""
API_SECRET = ""

# Base URL
# For India users: https://api.india.delta.exchange
# For Global users: https://api.delta.exchange
BASE_URL = "https://api.india.delta.exchange"

# Trading Settings
SYMBOL = "ETHUSD"  # The product symbol on Delta Exchange
# QUANTITY = 1       # Quantity in contracts (or ETH depending on contract specs, usually contracts for futures)
QUANTITIES = {
    "BTCUSD": 1,
    "ETHUSD": 1,
    "SOLUSD": 10
}
DEFAULT_QUANTITY = 1
LEVERAGE = 10
TIMEFRAME = "15m"   # 15 minute candles

# Indicator Settings
SUPERTREND_PERIOD = 2
SUPERTREND_MULTIPLIER = 2
HMA_PERIOD = 31

# Symbol Specific Configuration (Slope & Thresholds)
SYMBOL_CONFIG = {
    "ETHUSD": {
        "slope_scaling": 7900.0,
        "slope_threshold": 26
    },
    "SOLUSD": {
        "slope_scaling": 3000.0,
        "slope_threshold": 26
    },
    "BTCUSD": {
        "slope_scaling": 3000.0,
        "slope_threshold": 26
    }
}

# Fallback defaults
DEFAULT_SLOPE_SCALING = 3000.0
HMA_SLOPE_THRESHOLD = 26 


# System Settings
DRY_RUN = True  # Set to False to actually place trades
LOG_LEVEL = "INFO"

# Telegram Notification Configuration
TELEGRAM_ENABLED = True # Set to True after filling credentials
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = "" # ShivakumarGorasa
