import config
import delta_exchange
import indicators
import pandas as pd
from datetime import datetime, timedelta

# Setup
exchange = delta_exchange.DeltaExchange(config.API_KEY, config.API_SECRET, base_url=config.BASE_URL)
symbol = "SOLUSD"
timeframe = "15m"

print(f"Diagnosing {symbol} for recent candles...")

# Fetch Data
end_dt = datetime.now()
start_dt = end_dt - timedelta(days=2) # Last 2 days to match server

df = exchange.fetch_candles(symbol, timeframe=timeframe, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()))

if df.empty:
    print("Error: No data fetched.")
    exit()

# Calc Indicators
df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
df['HMA_Slope'] = indicators.calculate_slope_degrees(df['HMA'], scaling_factor=config.SLOPE_SCALING_FACTOR)
df = indicators.calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)

# Calc Trend Age
trend_starts = [0] * len(df)
current_start = 0
for i in range(1, len(df)):
    if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
        current_start = i
    trend_starts[i] = current_start

# Print last few candles
print(f"\n--- LOGIC CHECK (Thresholds: Slope +/-{config.HMA_SLOPE_THRESHOLD}, Age <= 1) ---")
print(f"{'Time':<20} | {'Price':<10} | {'Trend':<5} | {'Slope':<10} | {'Age':<5} | {'Result'}")
print("-" * 80)

for i in range(len(df)-5, len(df)):
    row = df.iloc[i]
    time_str = row['time'] # timestamp
    price = row['close']
    trend = row['SupertrendTrend']
    slope = row['HMA_Slope']
    age = i - trend_starts[i]
    
    # Logic Re-eval
    res = "SKIP"
    if trend == 1:
        if slope >= config.HMA_SLOPE_THRESHOLD and age <= 1: res = "BUY SIGNAL"
        elif slope < config.HMA_SLOPE_THRESHOLD: res = "SKIP (Low Slope)"
        elif age > 1: res = "SKIP (Age > 1)"
    else:
        if slope <= -config.HMA_SLOPE_THRESHOLD and age <= 1: res = "SELL SIGNAL"
        elif slope > -config.HMA_SLOPE_THRESHOLD: res = "SKIP (Low Slope)"
        elif age > 1: res = "SKIP (Age > 1)"

    print(f"{str(time_str):<20} | {price:<10.2f} | {trend:<5} | {slope:<10.2f} | {age:<5} | {res}")
