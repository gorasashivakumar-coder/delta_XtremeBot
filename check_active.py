from delta_exchange import DeltaExchange
import config
from indicators import calculate_supertrend, calculate_hma, calculate_slope_degrees
import strategy_utils
import bot
import pandas as pd
import time
import logging

# Mock logging
logging.basicConfig(level=logging.ERROR)

def check_active():
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    print("\n" + "="*50)
    print(" ACTIVE POSITIONS DEBUGGER (DRY RUN MODE) ")
    print("="*50)
    
    symbols = ["ETHUSD", "SOLUSD", "BTCUSD"]
    
    for symbol in symbols:
        try:
            df = bot.get_latest_data(exchange, symbol)
            
            # Run Strategy Scan
            trades = strategy_utils.scan_trades_for_df(df, symbol)
            
            print(f"\nScanning {symbol}...")
            if not trades:
                print("No trades found in history.")
                continue
                
            last_trade = trades[-1]
            print(f"Latest Trade Status: {last_trade['status']}")
            print(f"Type: {last_trade['type']}")
            print(f"Entry Time: {last_trade['entry_time']}")
            
            if last_trade['status'] == 'OPEN':
                print(">> CONCLUSION: Bot considers this an ACTIVE POSITION.")
                print(">> CONSEQUENCE: Bot will SKIP 'Entry Logic' (Signal Alert) and go to 'Exit Logic'.")
            else:
                print(">> CONCLUSION: No Active Position.")
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    check_active()
