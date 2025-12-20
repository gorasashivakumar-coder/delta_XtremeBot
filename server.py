from flask import Flask, jsonify, render_template_string
from datetime import datetime, timedelta
import pytz
import config
from delta_exchange import DeltaExchange
import indicators
import strategy_utils
import pandas as pd
import threading
import time
import pytz
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize Exchange
exchange = DeltaExchange(config.API_KEY, config.API_SECRET, base_url=config.BASE_URL)

SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD"]
CACHE = {
    "signals": {},
    "history": [],
    "last_update": None
}



def monitor_market():
    """Background task to update market data periodically"""
    while True:
        new_data = {}
        all_trades = []
        
        for symbol in SYMBOLS:
            try:
                tf = config.TIMEFRAME
                start_dt = datetime.now() - timedelta(days=2) 
                end_dt = datetime.now()
                
                print(f"Fetching {symbol}...", flush=True)
                df = exchange.fetch_candles(symbol, timeframe=tf, start=int(start_dt.timestamp()), end=int(end_dt.timestamp()))
                
                if df is None or df.empty:
                    new_data[symbol] = {"error": "No Data"}
                    continue
                
                # Indicators
                sym_config = config.SYMBOL_CONFIG.get(symbol, {})
                slope_threshold = sym_config.get("slope_threshold", config.HMA_SLOPE_THRESHOLD)
                slope_scaling = sym_config.get("slope_scaling", config.DEFAULT_SLOPE_SCALING)

                df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
                df['HMA_Slope'] = indicators.calculate_slope_degrees(df['HMA'], scaling_factor=slope_scaling)
                df = indicators.calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
                
                # --- History Scanner ---
                symbol_trades = strategy_utils.scan_trades_for_df(df, symbol)
                all_trades.extend(symbol_trades)
                
                # Calculate Accuracy (Win Rate)
                closed_trades = [t for t in symbol_trades if t['status'] == 'CLOSED']
                winning_trades = [t for t in closed_trades if t['pnl'] > 0]
                total_closed = len(closed_trades)
                accuracy = (len(winning_trades) / total_closed * 100) if total_closed > 0 else 0
                # -----------------------

                # Latest State
                last_row = df.iloc[-1]
                price = last_row['close']
                trend = last_row['SupertrendTrend']
                slope = last_row['HMA_Slope']
                supertrend_val = last_row['Supertrend']
                
                # Trend Age (Latest)
                trend_age = 0
                for i in range(len(df)-1, 0, -1):
                    if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
                        trend_age = len(df) - 1 - i
                        break
                    if i == 1: trend_age = 999 
                
                # Signal
                signal_text = "HOLD"
                signal_color = "gray"
                
                if trend == 1:
                    status = "BULLISH"
                    if slope >= slope_threshold and trend_age <= 1:
                         signal_text = "ENTRY LONG"
                         signal_color = "green"
                    elif slope >= slope_threshold:
                         signal_text = "HOLD LONG"
                         signal_color = "green"
                    else:
                         signal_text = "WEAK BULLISH"
                         signal_color = "yellow"
                else:
                    status = "BEARISH"
                    if slope <= -slope_threshold and trend_age <= 1:
                         signal_text = "ENTRY SHORT"
                         signal_color = "red"
                    elif slope <= -slope_threshold:
                         signal_text = "HOLD SHORT"
                         signal_color = "red"
                    else:
                         signal_text = "WEAK BEARISH"
                         signal_color = "yellow"

                new_data[symbol] = {
                    "price": price,
                    "trend": status,
                    "slope": round(float(slope), 2),
                    "slope_threshold": slope_threshold,
                    "supertrend": round(float(supertrend_val), 2),
                    "signal": signal_text,
                    "signal_color": signal_color,
                    "trend_age": trend_age,
                    "accuracy": round(accuracy, 1),
                    "total_trades": total_closed,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }

            except Exception as e:
                print(f"Error processing {symbol}: {e}", flush=True)
                new_data[symbol] = {"error": str(e)}
        
        # Sort trades by time (descending)
        all_trades.sort(key=lambda x: x['entry_time'], reverse=True)
        
        # Convert Timestamps to strings for JSON (in IST)
        ist = pytz.timezone('Asia/Kolkata')
        for t in all_trades:
            if isinstance(t['entry_time'], pd.Timestamp):
                # Assuming original is UTC or naive (Delta API usually returns UTC)
                if t['entry_time'].tz is None:
                    t['entry_time'] = t['entry_time'].tz_localize('UTC')
                t['entry_time'] = t['entry_time'].astimezone(ist).strftime("%Y-%m-%d %H:%M")
            
            if isinstance(t['exit_time'], pd.Timestamp):
                if t['exit_time'].tz is None:
                    t['exit_time'] = t['exit_time'].tz_localize('UTC')
                t['exit_time'] = t['exit_time'].astimezone(ist).strftime("%Y-%m-%d %H:%M")

        if new_data:
            CACHE["signals"] = new_data
            CACHE["history"] = all_trades
            CACHE["last_update"] = datetime.now()
        
        time.sleep(10)

# Start Background Thread
t = threading.Thread(target=monitor_market)
t.daemon = True
t.start()

@app.route('/')
def dashboard():
    with open('dashboard.html', 'r') as f:
        return f.read()

@app.route('/api/data')
def get_data():
    return jsonify(CACHE)

if __name__ == '__main__':
    print("Starting Dashboard Server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
