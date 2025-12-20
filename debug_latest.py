from delta_exchange import DeltaExchange
import config
from indicators import calculate_supertrend, calculate_hma, calculate_slope_degrees
import pandas as pd
import time
import logging

logging.basicConfig(level=logging.INFO)

def check_logic():
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    symbols = ["BTCUSD", "ETHUSD", "SOLUSD"]
    
    print("\n" + "="*50)
    print(" LOGIC DEBUGGER ")
    print("="*50)
    
    for symbol in symbols:
        try:
            # Fetch same data as bot
            end_time = int(time.time())
            start_time = end_time - (25 * 60 * 60)
            
            df = exchange.fetch_candles(symbol, timeframe=config.TIMEFRAME, start=start_time, end=end_time)
            
            # Indicators
            df = calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
            hma = calculate_hma(df['close'], period=config.HMA_PERIOD)
            sym_config = config.SYMBOL_CONFIG.get(symbol, {})
            scaling = sym_config.get("slope_scaling", config.DEFAULT_SLOPE_SCALING)
            threshold = sym_config.get("slope_threshold", config.HMA_SLOPE_THRESHOLD)
            
            slope = calculate_slope_degrees(hma, scaling)
            df['HMA_Slope'] = slope
            
            # Get Last 2 Candles
            last = df.iloc[-2] # Last Closed Candle
            prev = df.iloc[-3]
            
            curr_trend = last['SupertrendTrend']
            prev_trend = prev['SupertrendTrend']
            curr_slope = last['HMA_Slope']
            
            # Recalculate Age
            trend_age = 0
            for i in range(len(df)-2, 0, -1):
                if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
                    trend_age = (len(df)-2) - i
                    break
                    
            print(f"\nSymbol: {symbol}")
            print(f"Time: {last['time']}")
            print(f"Trend: {curr_trend} (Prev: {prev_trend}) -> Flip? {curr_trend != prev_trend}")
            print(f"Age: {trend_age} (Must be <= 1 for Signal)")
            print(f"Slope: {curr_slope:.2f} (Threshold: {threshold}) -> Valid? {abs(curr_slope) >= threshold}")
            
            # Logic Check
            is_buy = (curr_trend == 1 and curr_slope >= threshold and trend_age <= 1)
            is_sell = (curr_trend == -1 and curr_slope <= -threshold and trend_age <= 1)
            
            if is_buy:
                print(">>> RESULT: VALID BUY SIGNAL <<<")
            elif is_sell:
                print(">>> RESULT: VALID SELL SIGNAL <<<")
            else:
                print(">>> RESULT: NO SIGNAL")
                if trend_age > 1: print("   Reason: Trend too old")
                if abs(curr_slope) < threshold: print("   Reason: Slope too weak")
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    check_logic()
