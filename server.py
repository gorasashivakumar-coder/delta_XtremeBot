from flask import Flask, jsonify, render_template_string
import config
import delta_exchange
import indicators
import pandas as pd
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# Initialize Exchange
exchange = delta_exchange.DeltaExchange(config.API_KEY, config.API_SECRET, base_url=config.BASE_URL)

SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD"]
CACHE = {
    "signals": {},
    "history": [],
    "last_update": None
}

def scan_trades_for_df(df, symbol):
    """
    Scans the dataframe for historical trades based on strategy logic.
    Returns a list of trade dicts.
    """
    trades = []
    in_position = 0 # 0, 1, -1
    entry_price = 0.0
    entry_time = None
    
    # We iterate from row 1 (need prev row for trend flip checks if needed, 
    # but we have trend_age logic which might need lookback.
    # Simpler: Iterate row by row simulating the bot.
    
    # Need to look back for Trend Age calculation dynamically or just trust the columns if we pre-calc them?
    # We pre-calc indicators. Let's pre-calc 'Trend Start' or 'Age' column.
    
    # Pre-calc Trend Age for entire DF
    # This is O(N) but N is small (2 days ~ 200 rows)
    trend_starts = [0] * len(df)
    current_start = 0
    for i in range(1, len(df)):
        if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
            current_start = i
        trend_starts[i] = current_start
        
    for i in range(1, len(df)):
        row = df.iloc[i]
        curr_price = row['close']
        trend = row['SupertrendTrend']
        slope = row['HMA_Slope']
        time_str = row['time'] # timestamp object
        
        # Calculate Age
        trend_age = i - trend_starts[i]
        
        # Check Exit first
        if in_position == 1 and trend == -1:
            # Exit Long
            pnl = curr_price - entry_price
            trades.append({
                "symbol": symbol,
                "type": "LONG",
                "entry_price": entry_price,
                "exit_price": curr_price,
                "entry_time": entry_time,
                "exit_time": time_str,
                "pnl": round(pnl, 2),
                "status": "CLOSED"
            })
            in_position = 0
            
        elif in_position == -1 and trend == 1:
            # Exit Short
            pnl = entry_price - curr_price
            trades.append({
                "symbol": symbol,
                "type": "SHORT",
                "entry_price": entry_price,
                "exit_price": curr_price,
                "entry_time": entry_time,
                "exit_time": time_str,
                "pnl": round(pnl, 2),
                "status": "CLOSED"
            })
            in_position = 0
            
        # Check Entry
        if in_position == 0:
            # BUY
            if trend == 1 and slope >= config.HMA_SLOPE_THRESHOLD and trend_age <= 1:
                in_position = 1
                entry_price = curr_price
                entry_time = time_str
                
            # SELL
            elif trend == -1 and slope <= -config.HMA_SLOPE_THRESHOLD and trend_age <= 1:
                in_position = -1
                entry_price = curr_price
                entry_time = time_str
    
    # If still in position, add Open Trade
    if in_position != 0:
        curr_price = df.iloc[-1]['close']
        pnl = (curr_price - entry_price) if in_position == 1 else (entry_price - curr_price)
        trades.append({
            "symbol": symbol,
            "type": "LONG" if in_position == 1 else "SHORT",
            "entry_price": entry_price,
            "exit_price": curr_price,
            "entry_time": entry_time,
            "exit_time": "-",
            "pnl": round(pnl, 2),
            "status": "OPEN"
        })
        
    return trades

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
                df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
                df['HMA_Slope'] = indicators.calculate_slope_degrees(df['HMA'], scaling_factor=config.SLOPE_SCALING_FACTOR)
                df = indicators.calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
                
                # --- History Scanner ---
                symbol_trades = scan_trades_for_df(df, symbol)
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
                    if slope >= config.HMA_SLOPE_THRESHOLD and trend_age <= 1:
                         signal_text = "ENTRY LONG"
                         signal_color = "green"
                    elif slope >= config.HMA_SLOPE_THRESHOLD:
                         signal_text = "HOLD LONG"
                         signal_color = "green"
                    else:
                         signal_text = "WEAK BULLISH"
                         signal_color = "yellow"
                else:
                    status = "BEARISH"
                    if slope <= -config.HMA_SLOPE_THRESHOLD and trend_age <= 1:
                         signal_text = "ENTRY SHORT"
                         signal_color = "red"
                    elif slope <= -config.HMA_SLOPE_THRESHOLD:
                         signal_text = "HOLD SHORT"
                         signal_color = "red"
                    else:
                         signal_text = "WEAK BEARISH"
                         signal_color = "yellow"

                new_data[symbol] = {
                    "price": price,
                    "trend": status,
                    "slope": round(float(slope), 2),
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
        
        # Convert Timestamps to strings for JSON
        for t in all_trades:
            if isinstance(t['entry_time'], pd.Timestamp):
                t['entry_time'] = t['entry_time'].strftime("%Y-%m-%d %H:%M")
            if isinstance(t['exit_time'], pd.Timestamp):
                t['exit_time'] = t['exit_time'].strftime("%Y-%m-%d %H:%M")

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
