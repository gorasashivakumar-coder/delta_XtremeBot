import config
from delta_exchange import DeltaExchange
import indicators
from datetime import datetime, timedelta
import pandas as pd
import math
import numpy as np

def calibrate():
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, base_url=config.BASE_URL)
    symbol = "ETHUSD"
    
    print(f"Fetching data for {symbol}...")
    start_dt = datetime.now() - timedelta(days=2)
    end_dt = datetime.now()
    
    df = exchange.fetch_candles(symbol, timeframe=config.TIMEFRAME, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()))
    
    if df is None or df.empty:
        print("No data received")
        return

    # Calculate Indicators with current config to find the row
    df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
    
    # Calculate percentage change series which is the base for slope
    # slope = degrees(atan(pct_change * factor))
    # so pct_change = tan(radians(slope)) / factor
    series = df['HMA']
    pct_changes = series.pct_change()
    
    # Find the target candle : 08:15 UTC
    # Since we don't know the exact day (probably today Dec 20), we search for 08:15 in last few rows
    target_row_idx = -1
    target_time_str = "08:15:00"
    
    print(f"Searching for {target_time_str}...")
    for i in range(len(df)-1, 0, -1):
        t_str = str(df.iloc[i]['time']) # Expecting format like 2025-12-20 08:15:00
        if target_time_str in t_str:
            target_row_idx = i
            print(f"Found target candle at index {i}: {t_str}")
            break
            
    if target_row_idx == -1:
        print("Target candle not found!")
        return

    # Get the pct_change for this candle
    target_pct_change = pct_changes.iloc[target_row_idx]
    
    print(f"HMA pct_change at target: {target_pct_change}")
    
    # Goal: We want slope >= 26 degrees
    # Target Angle = 26
    # equation: 26 = degrees(atan(pct_change * new_factor))
    # tan(radians(26)) = pct_change * new_factor
    # new_factor = tan(radians(26)) / pct_change
    
    target_angle = 26.0
    rad_angle = math.radians(target_angle)
    tan_angle = math.tan(rad_angle)
    
    required_factor = tan_angle / target_pct_change
    
    print(f"Target Angle: {target_angle} degrees")
    print(f"Required Scaling Factor: {required_factor:.2f}")
    
    # Verification
    check_slope = math.degrees(math.atan(target_pct_change * required_factor))
    print(f"Verification Check: atan({target_pct_change:.6f} * {required_factor:.2f}) -> {check_slope:.2f} degrees")
    
    # Suggest a round number
    suggested = round(required_factor / 100) * 100
    print(f"Suggested Round Factor: {suggested}")

if __name__ == "__main__":
    calibrate()
