import config
from delta_exchange import DeltaExchange
import indicators
from datetime import datetime, timedelta
import pandas as pd

def check_signal():
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, base_url=config.BASE_URL)
    symbol = "ETHUSD"
    
    print(f"Fetching data for {symbol}...")
    start_dt = datetime.now() - timedelta(days=2)
    end_dt = datetime.now()
    
    df = exchange.fetch_candles(symbol, timeframe=config.TIMEFRAME, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()))
    
    if df is None or df.empty:
        print("No data received")
        return

    # Indicators
    sym_config = config.SYMBOL_CONFIG.get(symbol, {})
    slope_threshold = sym_config.get("slope_threshold", config.HMA_SLOPE_THRESHOLD)
    slope_scaling = sym_config.get("slope_scaling", config.DEFAULT_SLOPE_SCALING)

    df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
    df['HMA_Slope'] = indicators.calculate_slope_degrees(df['HMA'], scaling_factor=slope_scaling)
    df = indicators.calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
    
    # Latest State
    last_row = df.iloc[-1]
    price = last_row['close']
    trend = last_row['SupertrendTrend']
    slope = last_row['HMA_Slope']
    
    # Trend Age (Latest)
    trend_age = 0
    for i in range(len(df)-1, 0, -1):
        if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
            trend_age = len(df) - 1 - i
            break
        if i == 1: trend_age = 999 

    print(f"Time: {last_row['time']}")
    print(f"Price: {price}")
    print(f"Trend: {trend} (1=Bull, -1=Bear)")
    print(f"Trend Age: {trend_age}")
    print(f"Slope: {slope}")
    print(f"Threshold: {slope_threshold}")
    
    # Signal Logic from server.py (updated)
    signal_text = "HOLD"
    if trend == 1:
        if slope >= slope_threshold and trend_age <= 1:
                signal_text = "ENTRY LONG"
        elif slope >= slope_threshold:
                signal_text = "HOLD LONG"
        else:
                signal_text = "WEAK BULLISH"
    else:
        if slope <= -slope_threshold and trend_age <= 1:
                signal_text = "ENTRY SHORT"
        elif slope <= -slope_threshold:
                signal_text = "HOLD SHORT"
        else:
                signal_text = "WEAK BEARISH"
                
    print(f"Calculated Signal: {signal_text}")
    
    print("\n--- Last 5 Candles ---")
    for i in range(len(df)-5, len(df)):
        row = df.iloc[i]
        curr_slope = row['HMA_Slope']
        curr_trend = row['SupertrendTrend']
        
        # Calculate Trend Age for this historical row
        row_trend_age = 0
        for j in range(i, 0, -1):
             if df.iloc[j]['SupertrendTrend'] != df.iloc[j-1]['SupertrendTrend']:
                 row_trend_age = i - j
                 break
             if j == 1: row_trend_age = 999

        print(f"Time: {row['time']} | Trend: {curr_trend} | Slope: {curr_slope:.2f} | Age: {row_trend_age}")

if __name__ == "__main__":
    check_signal()

