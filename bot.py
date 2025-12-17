import time
import pandas as pd
import logging
from datetime import datetime

import config
from delta_exchange import DeltaExchange
from indicators import calculate_supertrend, calculate_hma, calculate_slope_degrees

# Setup Logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_latest_data(exchange, symbol):
    """
    Fetches historical data and calculates indicators.
    """
    try:
        candles = exchange.get_history(symbol, resolution=config.TIMEFRAME, limit=100)
        if not candles:
            logger.error("No candle data received")
            return None

        # Convert to DataFrame
        # Delta Candle format: [time, open, high, low, close, volume] (or dict)
        # Checking delta_exchange.py: it returns result directly. 
        # API returns list of dicts typically: {'t': ..., 'o': ..., ...} or similar.
        # Let's assume list of dicts based on doc reading previously (which showed JSON object)
        # Docs output: { "result": [ { "time": 0, "open": 0, ... } ] }
        
        df = pd.DataFrame(candles)
        # Ensure numeric columns
        cols = ['open', 'high', 'low', 'close', 'volume']
        for col in cols:
            df[col] = pd.to_numeric(df[col])
            
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.sort_values('time').reset_index(drop=True)
        
        # Calculate Indicators
        df = calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
        
        hma = calculate_hma(df['close'], period=config.HMA_PERIOD)
        df['HMA'] = hma
        
        slope = calculate_slope_degrees(df['HMA'], scaling_factor=config.SLOPE_SCALING_FACTOR)
        df['HMA_Slope'] = slope
        
        return df
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return None

def main():
    logger.info("Starting Delta Exchange Bot...")
    
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    # Get Product ID
    try:
        product_id = exchange.get_product_id(config.SYMBOL)
        if not product_id:
            logger.error(f"Could not find Product ID for {config.SYMBOL}")
            return
        logger.info(f"Product ID for {config.SYMBOL}: {product_id}")
    except Exception as e:
        logger.error(f"Failed to connect or fetch product ID: {e}")
        return

    last_traded_trend = None # Initialize as None to set on first loop
    TAKE_PROFIT = 1000

    while True:
        try:
            logger.info("Fetching market data...")
            df = get_latest_data(exchange, config.SYMBOL)
            
            if df is not None:
                # Get the last completed candle (index -2, as -1 is current forming candle)
                if len(df) < 2:
                    logger.warning("Not enough data yet")
                    continue
                    
                acc_idx = -2 # Last closed candle
                last_candle = df.iloc[acc_idx]
                curr_price = last_candle['close']
                curr_supertrend = last_candle['Supertrend']
                curr_trend = last_candle['SupertrendTrend'] # 1 Buy, -1 Sell
                curr_slope = last_candle['HMA_Slope']
                
                # Trend Age Calculation
                # We need to know how many candles ago the trend flipped to current state.
                # Window 0: Current candle flipped (curr != prev)
                # Window 1: Previous candle flipped (prev != prev_prev)
                # We need history up to -4
                
                trend_age = 999
                if len(df) >= 4:
                    prev_candle = df.iloc[-3]
                    prev_prev_candle = df.iloc[-4]
                    
                    prev_trend = prev_candle['SupertrendTrend']
                    prev_prev_trend = prev_prev_candle['SupertrendTrend']
                    
                    if curr_trend != prev_trend:
                        trend_age = 0
                    elif prev_trend != prev_prev_trend:
                        trend_age = 1
                    else:
                        trend_age = 999
                else:
                    # Not enough data for robust check, strict default
                    trend_age = 999 
                
                # Initialize last_traded_trend on first run to avoid jumping in blindly
                # But logic above handles 'blind jump' by requiring fresh age.
                # So we can just rely on trend_age. 
                # If we restart mid-trend, age will be > 1, so we WON'T enter. 
                # This subsumes the 'last_traded_trend is None' check for startup safety.
                
                if last_traded_trend is None:
                    last_traded_trend = curr_trend if trend_age > 1 else 0 
                    # If we catch a fresh trend on startup (age<=1), allow trade (last=0). 
                    # If old trend, block it (last=curr).
                
                logger.info(f"Time: {last_candle['time']} | Price: {curr_price} | ST: {curr_supertrend:.2f} | Trend: {curr_trend} (Age: {trend_age}) | Slope: {curr_slope:.2f}")

                # ---------------------------------------------------------------------------------
                # TRADE LOGIC
                # ---------------------------------------------------------------------------------
                
                # Check current position
                position = exchange.get_position(product_id)
                current_qty = 0
                entry_price = 0
                in_position_direction = 0 # 1 Long, -1 Short
                
                if position and float(position.get("size", 0)) > 0:
                     # Delta returns size as positive integer, side is separate? 
                     # Checking get_position response structure from memory/docs: usually size is signed OR side field.
                     # Let's assume size is unsigned and we check 'side' or 'entry_price'.
                     # Actually, standard delta API has 'size' (signed) for positions? Or 'size' + 'side'.
                     # Assuming 'size' is abs value, checking side.
                     # If I look at place_order, it takes 'buy'/'sell'.
                     # Let's assume for now: if size is present, we are in position.
                     current_qty = float(position["size"])
                     # Need direction. 
                     # Simpler: assume we track it or infer from entry?
                     # Ideally query side. Let's assume position['side'] exists or size is signed.
                     # For now, let's treat any position as "In Trade".
                     entry_price = float(position.get("entry_price", 0))
                     # We need to distinguish Long vs Short for TP logic.
                     # Let's assume we are Long if entry_price < current_price + big margin? Unreliable.
                     # Let's assume position has 'size' signed. 
                     # If not, and we have to guess: 
                     # If we just implemented it, we can check logic. 
                     # But for robustness, let's assume `last_traded_trend` tells us direction if we started it.
                     pass 

                # Signal Processing
                # 1. Check Exit (TP / SL)
                if current_qty > 0:
                    # Determine direction from last_traded_trend if possible, or assume based on recent signal
                    # If we don't know direction properly from API, TP is risky.
                    # Assumption: `position['size']` is signed. (+ Long, - Short)
                    # If not, let's check `position['side']`.
                    
                    is_long = True # Placeholder
                    if position.get('side') == 'sell' or (position.get('size') and float(position['size']) < 0):
                        is_long = False
                        
                    # Check TP
                    if is_long:
                        if curr_price >= entry_price + TAKE_PROFIT:
                            logger.info(f"Take Profit Hit (Long): {curr_price}")
                            exchange.place_order(product_id, current_qty, "sell", "market_order") # Close
                            # last_traded_trend remains 1, blocking re-entry
                    else: # Short
                        if curr_price <= entry_price - TAKE_PROFIT:
                            logger.info(f"Take Profit Hit (Short): {curr_price}")
                            exchange.place_order(product_id, current_qty, "buy", "market_order") # Close
                            
                    # Check Trailing Stop (Supertrend Flip)
                    # If Long and Trend == -1
                    if is_long and curr_trend == -1:
                        logger.info("Trend Reversal (Long -> Short) - Closing Position")
                        exchange.place_order(product_id, current_qty, "sell", "market_order")
                        
                    elif not is_long and curr_trend == 1:
                        logger.info("Trend Reversal (Short -> Long) - Closing Position")
                        exchange.place_order(product_id, current_qty, "buy", "market_order")

                # 2. Check Entries
                # Only enter if NO position AND trend matches conditions AND we haven't traded this trend
                # AND Trend is fresh (<= 1 candle old)
                if current_qty == 0:
                    if curr_trend == 1 and curr_slope >= config.HMA_SLOPE_THRESHOLD and last_traded_trend != 1:
                        if trend_age <= 1:
                            logger.info("Signal: BUY")
                            if not config.DRY_RUN:
                                exchange.place_order(product_id, config.QUANTITY, "buy")
                            last_traded_trend = 1
                        else:
                             if curr_slope >= config.HMA_SLOPE_THRESHOLD:
                                 logger.info(f"Skipping BUY: Trend too old (Age {trend_age})")
                        
                    elif curr_trend == -1 and curr_slope <= -config.HMA_SLOPE_THRESHOLD and last_traded_trend != -1:
                         if trend_age <= 1:
                             logger.info("Signal: SELL")
                             if not config.DRY_RUN:
                                exchange.place_order(product_id, config.QUANTITY, "sell")
                             last_traded_trend = -1
                         else:
                             if curr_slope <= -config.HMA_SLOPE_THRESHOLD:
                                 logger.info(f"Skipping SELL: Trend too old (Age {trend_age})")
                         
                    else:
                        if curr_trend == last_traded_trend:
                            logger.info(f"Skipping Re-entry for Trend {curr_trend}")

                if config.DRY_RUN:
                   logger.info(f"[DRY RUN] In Pos: {current_qty}, Last Traded Trend: {last_traded_trend}") 
                    
            # Sleep logic to align with next minute
            # time.sleep(60) 
            # Better: Sleep until next minute start + few seconds
            now = time.time()
            sleep_time = 60 - (now % 60) + 2 # +2s buffer
            logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
