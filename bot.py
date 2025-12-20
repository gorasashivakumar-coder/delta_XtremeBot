import time
import pandas as pd
import logging
from datetime import datetime

import config
from delta_exchange import DeltaExchange
from indicators import calculate_supertrend, calculate_hma, calculate_slope_degrees
import notifier
import strategy_utils

# Setup Logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_latest_data(exchange, symbol):
    """
    Fetches historical data and calculates indicators.
    """
    try:
        # Calculate time range for last 100 candles (approx 25 hours for 15m)
        end_time = int(time.time())
        start_time = end_time - (25 * 60 * 60)
        
        df = exchange.fetch_candles(symbol, timeframe=config.TIMEFRAME, start=start_time, end=end_time)
        
        if df is None or df.empty:
            logger.error(f"{symbol}: No candle data received")
            return None

        # Calculate Indicators
        df = calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
        
        hma = calculate_hma(df['close'], period=config.HMA_PERIOD)
        df['HMA'] = hma
        
        # Get Symbol Config
        sym_config = config.SYMBOL_CONFIG.get(symbol, {})
        scaling = sym_config.get("slope_scaling", config.DEFAULT_SLOPE_SCALING)
        
        slope = calculate_slope_degrees(df['HMA'], scaling_factor=scaling)
        df['HMA_Slope'] = slope
        
        return df
    except Exception as e:
        logger.error(f"Error processing data for {symbol}: {e}")
        return None

def process_symbol(exchange, symbol, state):
    """
    Process trading logic for a single symbol.
    """
    try:
        # Get Product ID
        product_id = state.get('product_id')
        if not product_id:
            product_id = exchange.get_product_id(symbol)
            if not product_id:
                logger.error(f"Could not find Product ID for {symbol}")
                return
            state['product_id'] = product_id

        # Get Data
        df = get_latest_data(exchange, symbol)
        if df is None: return

        if len(df) < 2:
            logger.warning(f"{symbol}: Not enough data yet")
            return
            
        acc_idx = -2 # Last closed candle
        last_candle = df.iloc[acc_idx]
        curr_price = last_candle['close']
        curr_trend = last_candle['SupertrendTrend'] # 1 Buy, -1 Sell
        curr_slope = last_candle['HMA_Slope']
        
        # Trend Age
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
        
        # Configs
        qty = config.QUANTITIES.get(symbol, config.DEFAULT_QUANTITY)
        sym_config = config.SYMBOL_CONFIG.get(symbol, {})
        slope_threshold = sym_config.get("slope_threshold", config.HMA_SLOPE_THRESHOLD)
        
        # State
        last_traded_trend = state.get('last_traded_trend')
        
        # Initialize last_traded_trend on first run
        if last_traded_trend is None:
            # If we catch a fresh trend on startup (age<=1), allow trade (last=0). 
            # If old trend, block it (set to current).
            state['last_traded_trend'] = curr_trend if trend_age > 1 else 0
            last_traded_trend = state['last_traded_trend']

        logger.info(f"{symbol} | Price: {curr_price} | Trend: {curr_trend} (Age: {trend_age}) | Slope: {curr_slope:.2f} (Thresh: {slope_threshold})")

        # Position Check
        if config.DRY_RUN:
            # SIMULATED POSITION (from Strategy)
            trades = strategy_utils.scan_trades_for_df(df, symbol)
            position = {}
            if trades and trades[-1]['status'] == 'OPEN':
                t = trades[-1]
                # Mock structure similar to exchange response
                position = {
                    "size": config.QUANTITIES.get(symbol, config.DEFAULT_QUANTITY) * (1 if t['type']=='LONG' else -1),
                    "entry_price": float(t['entry_price']),
                    "side": 'buy' if t['type']=='LONG' else 'sell',
                    "unrealized_pl": float(t['pnl'])
                }
        else:
            # REAL POSITION (from Exchange)
            position = exchange.get_position(product_id)

        current_qty = 0
        entry_price = 0
        
        if position and float(position.get("size", 0)) != 0:
             current_qty = abs(float(position["size"])) # size can be negative from exchange
             entry_price = float(position.get("entry_price", 0))

        TAKE_PROFIT = 1000

        # 1. Exit Logic
        if current_qty > 0:
            # Determine direction
            is_long = True 
            if position.get('side') == 'sell' or (position.get('size') and float(position['size']) < 0):
                is_long = False
                
            # TP
            if is_long and curr_price >= entry_price + TAKE_PROFIT:
                logger.info(f"{symbol}: Take Profit Hit (Long)")
                if not config.DRY_RUN:
                    exchange.place_order(product_id, current_qty, "sell", "market_order")
            elif not is_long and curr_price <= entry_price - TAKE_PROFIT:
                logger.info(f"{symbol}: Take Profit Hit (Short)")
                if not config.DRY_RUN:
                    exchange.place_order(product_id, current_qty, "buy", "market_order")
                
            # Trend Reversal
            if is_long and curr_trend == -1:
                logger.info(f"{symbol}: Trend Reversal (Long -> Short) - Closing")
                if not config.DRY_RUN:
                    exchange.place_order(product_id, current_qty, "sell", "market_order")
            elif not is_long and curr_trend == 1:
                logger.info(f"{symbol}: Trend Reversal (Short -> Long) - Closing")
                if not config.DRY_RUN:
                    exchange.place_order(product_id, current_qty, "buy", "market_order")

        # 2. Entry Logic
        if current_qty == 0:
            if curr_trend == 1 and curr_slope >= slope_threshold and last_traded_trend != 1:
                if trend_age <= 1:
                    msg = f"🚀 **BUY SIGNAL** #{symbol}\nPrice: {curr_price}\nSlope: {curr_slope:.2f}/{slope_threshold}"
                    logger.info(f"{symbol}: {msg.replace('*','').replace(chr(10), ' ')}") # Log clean
                    notifier.send_telegram_message(msg)
                    
                    if not config.DRY_RUN:
                        exchange.place_order(product_id, qty, "buy")
                    state['last_traded_trend'] = 1
                else:
                     if curr_slope >= slope_threshold:
                         logger.info(f"{symbol}: Skipping BUY: Trend too old (Age {trend_age})")
                
            elif curr_trend == -1 and curr_slope <= -slope_threshold and last_traded_trend != -1:
                 if trend_age <= 1:
                     msg = f"🔻 **SELL SIGNAL** #{symbol}\nPrice: {curr_price}\nSlope: {curr_slope:.2f}/{slope_threshold}"
                     logger.info(f"{symbol}: {msg.replace('*','').replace(chr(10), ' ')}")
                     notifier.send_telegram_message(msg)
                     
                     if not config.DRY_RUN:
                        exchange.place_order(product_id, qty, "sell")
                     state['last_traded_trend'] = -1
                 else:
                     if curr_slope <= -slope_threshold:
                         logger.info(f"{symbol}: Skipping SELL: Trend too old (Age {trend_age})")
                 
            else:
                if curr_trend == last_traded_trend:
                    logger.info(f"{symbol}: Skipping Re-entry for Trend {curr_trend}")

    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")

def main():
    logger.info("Starting Delta Exchange Bot (Multi-Symbol)...")
    
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    # State tracking for each symbol
    # keys: 'product_id', 'last_traded_trend'
    bot_state = { sym: {} for sym in config.QUANTITIES.keys() }
    
    logger.info(f"Monitoring Symbols: {list(bot_state.keys())}")
    
    # --- STARTUP REPORT ---
    # --- STARTUP REPORT ---
    logger.info("Generating Startup Report...")
    history_data = {}
    active_positions = []
    
    for symbol in bot_state.keys():
        try:
            # 1. Get History & Data
            df = get_latest_data(exchange, symbol)
            if df is not None:
                 trades = strategy_utils.scan_trades_for_df(df, symbol)
                 
                 # 2. Check for Active Position in Strategy
                 if trades and trades[-1]['status'] == 'OPEN':
                     open_trade = trades[-1]
                     active_positions.append({
                        'symbol': symbol,
                        'size': config.QUANTITIES.get(symbol, config.DEFAULT_QUANTITY), # Strategy qty
                        'entry_price': float(open_trade['entry_price']),
                        'pnl': float(open_trade['pnl']),
                        'side': open_trade['type']
                    })

                 last_row = df.iloc[-2]
                 history_data[symbol] = {
                    'trades': trades,
                    'current': {
                        'trend': int(last_row['SupertrendTrend']),
                        'slope': float(last_row['HMA_Slope']),
                        'price': float(last_row['close']),
                        'threshold': config.SYMBOL_CONFIG.get(symbol, {}).get('slope_threshold', config.HMA_SLOPE_THRESHOLD)
                    }
                }
        except Exception as e:
            logger.error(f"Failed to generate report for {symbol}: {e}")
            
    notifier.send_startup_report(history_data, active_positions)
    
    # Send Individual Alerts for Active Positions (Late Start)
    if active_positions:
        for pos in active_positions:
            msg = f"🔔 **ACTIVE POSITION DETECTED** #{pos['symbol']}\n" \
                  f"Bot resumed tracking this trade.\n" \
                  f"Side: {pos['side']}\n" \
                  f"Entry: {pos['entry_price']}\n" \
                  f"uPnL: {pos['pnl']}"
            notifier.send_telegram_message(msg)
            
    # ----------------------

    while True:
        try:
            for symbol in bot_state.keys():
                process_symbol(exchange, symbol, bot_state[symbol])
                time.sleep(1) # Small delay between symbols to avoid rate limits
                
            # Sleep logic to align with next minute
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
