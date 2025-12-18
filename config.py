
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
QUANTITY = 1       # Quantity in contracts (or ETH depending on contract specs, usually contracts for futures)
LEVERAGE = 10
TIMEFRAME = "15m"   # 15 minute candles

# Indicator Settings
SUPERTREND_PERIOD = 2
SUPERTREND_MULTIPLIER = 2
HMA_PERIOD = 31

# Slope Threshold
# Angle in degrees. 
# NOTE: This is mathematically derived. You may need to tune 'SLOPE_SCALING_FACTOR' to match your visual chart.
HMA_SLOPE_THRESHOLD = 26 
# Scaling factor to make the slope calculation meaningful. 
# Price difference of 10 USD over 1 minute might need scaling to compare with "degrees" visually.
# A value of 3000 means roughly 0.016% move is 26 degrees (matching old sensitivity).
SLOPE_SCALING_FACTOR = 3000.0 

# System Settings
DRY_RUN = True  # Set to False to actually place trades
LOG_LEVEL = "INFO"
