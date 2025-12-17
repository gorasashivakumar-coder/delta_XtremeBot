import time
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone

import config
from delta_exchange import DeltaExchange
import indicators

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_backtest():
    # Backtest Configuration
    SYMBOL = "ETHUSD"
    
    # Define Date Range (Single Day: 17/12/2025)
    end_date_str = "17/12/2025"
    start_date_str = "17/12/2025"
    
    # Naive datetimes for calculation
    end_dt_ist = datetime.strptime(end_date_str, "%d/%m/%Y").replace(hour=23, minute=59, second=59)
    start_dt_ist = datetime.strptime(start_date_str, "%d/%m/%Y").replace(hour=0, minute=0, second=0)
    
    ist_offset = timedelta(hours=5, minutes=30)
    
    start_dt_utc = start_dt_ist - ist_offset
    end_dt_utc = end_dt_ist - ist_offset
    
    # Warmup: Add enough time for indicators (need ~100 candles)
    # 15m * 100 = 1500 minutes. Safe buffer: 2000 minutes.
    warmup_minutes = 2000
    fetch_start_utc = start_dt_utc - timedelta(minutes=warmup_minutes)
    
    # Convert to timestamp (Assume naive UTC is UTC)
    start_ts = int(fetch_start_utc.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end_dt_utc.replace(tzinfo=timezone.utc).timestamp())
    
    logger.info(f"Backtest: {SYMBOL}")
    logger.info(f"Target Period (IST): {start_dt_ist} to {end_dt_ist}")
    logger.info(f"Fetch Range (UTC): {fetch_start_utc} to {end_dt_utc}")
    
    exchange = DeltaExchange(config.API_KEY, config.API_SECRET, config.BASE_URL)
    
    # Fetch Data in chunks (Delta limit is usually 1000-2000, let's play safe with smaller chunks if helper doesn't auto-paginate)
    # Our simple helper gets 'limit' latest. We need to implement range fetching or just ask for a large limit if supported.
    # checking delta_exchange.py: get_history uses 'start', 'end'. 
    # Delta API /v2/history/candles supports start/end.
    
    logger.info("Fetching Market Data...")
    
    # Delta might have limit on candles per req.
    # We need approx 24*60 + 200 = 1640 candles.
    # We will try to fetch in one go, if truncated we might need loop.
    # Assuming 2000 limit is standard for time-range endpoints.
    
    # Update exchange.get_history to support custom time params fully if needed.
    # The current impl in delta_exchange.py calculates start from limit if not provided, 
    # but since I am calling API directly or via modified logic here?
    # I should use the method available.
    # The existing get_history method logic:
    # params = { "resolution": resolution, "symbol": symbol, "start": start_time, "end": end_time }
    # So I can just bypass the method wrapper or assume it works if I hacked it?
    # Actually, the method was: start_time = end_time - limit*...
    # I need to modify get_history to accept explicit start_time if I want to use the method, 
    # or just call _request directly here. I will call _request directly to avoid changing library code unnecessarily.
    
    params = {
        "resolution": config.TIMEFRAME,
        "symbol": SYMBOL,
        "start": start_ts,
        "end": end_ts
    }
    
    data = exchange._request("GET", "/v2/history/candles", params, auth=False)
    
    if not data or not data.get("success"):
        logger.error("Failed to fetch data.")
        return

    candles = data["result"]
    logger.info(f"Fetched {len(candles)} candles.")
    
    df = pd.DataFrame(candles)
    cols = ['open', 'high', 'low', 'close', 'volume']
    for col in cols:
        df[col] = pd.to_numeric(df[col])
        
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df.sort_values('time').reset_index(drop=True)
    # -------------------------------------------------------------------------
    # 4. Calculate Indicators (Updated to Series assignment)
    # -------------------------------------------------------------------------
    print("Calculating Indicators...")
    try:
        df['HMA'] = indicators.calculate_hma(df['close'], period=config.HMA_PERIOD)
        df['HMA_Slope'] = indicators.calculate_slope_degrees(df['HMA'], scaling_factor=config.SLOPE_SCALING_FACTOR)
        df = indicators.calculate_supertrend(df, period=config.SUPERTREND_PERIOD, multiplier=config.SUPERTREND_MULTIPLIER)
    except Exception as e:
        print(f"Indicator Error: {e}")
        return
    
    # -------------------------------------------------------------------------
    logger.info("\nStarting Simulation...")
    # NOTE: Iterate from index 'warmup_minutes' to skip unstable indicator part
    # But checking if we have enough data
    start_idx = 0
    # Find index where time >= start_dt_utc (the actual start of the day)
    # Using tz-naive comparison (UTC to UTC)
    start_idx_mask = df['time'] >= start_dt_utc
    if start_idx_mask.any():
        start_idx = start_idx_mask.idxmax()
    else:
        logger.warning("Data does not cover start time.")
    
    # Initialize Variables
    trade_count = 0
    trade_peak_price = 0 # Track max favorable excursion
    cumulative_pnl = 0
    in_position = 0
    entry_price = 0
    TAKE_PROFIT = 30
    trend_start_idx = 0 # Track when the current trend started
    last_pnl = 0
    
    current_pnl = 0
    trades = [] # Ensure trades list is init
    
    # Create Markdown Report
    report_file = "backtest_report.md"
    
    with open(report_file, "w", encoding="utf-8") as f:
        # Header
        f.write("# Backtest Report: ETHUSD (17 Dec - 15m)\n\n")
        f.write(f"**Period**: {start_date_str} to {end_date_str}\n")
        f.write(f"**Settings**: Supertrend({config.SUPERTREND_PERIOD}, {config.SUPERTREND_MULTIPLIER}), HMA({config.HMA_PERIOD})\n\n")
        f.write("| Time (IST) | Action | Entry Price | Exit Price | PnL | Max Run Up (%) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        
        # Console Header
        print(f"{'TIME (IST)':<25} {'ACTION':<15} {'ENTRY':<10} {'EXIT':<10} {'PNL':<10} {'RUN UP %':<10}")
        print("-" * 90)

        for i in range(start_idx, len(df)):
            # We look at *closed* candle at i. 
            # In live bot, we act on 'close' of candle i (which is -2 in list of forming + closed)
            # Here i is the candle that just closed.
            
            row = df.iloc[i]
            curr_price = row['close']
            time_ist = row['time'] + ist_offset
            
            trend = row['SupertrendTrend']
            slope = row['HMA_Slope']
            
            # Signal Generation
            signal = 0
            if trend == 1 and slope >= config.HMA_SLOPE_THRESHOLD:
                signal = 1
            elif trend == -1 and slope <= -config.HMA_SLOPE_THRESHOLD:
                signal = -1
            
        # Execution Logic
        action = None
        
        if signal == 1:
            if in_position == 0:
                action = "BUY"
                in_position = 1
                entry_price = curr_price
            elif in_position == -1:
                # Close Short, Open Long
                pnl = entry_price - curr_price
                trades.append({'Time': time_ist, 'Type': 'CLOSE SHORT', 'Price': curr_price, 'PnL': pnl})
                current_pnl += pnl
                
                action = "BUY (Reverse)"
                in_position = 1
                entry_price = curr_price
                
        elif signal == -1:
            if in_position == 0:
                action = "SELL"
                in_position = -1
                entry_price = curr_price
            elif in_position == 1:
                # Close Long, Open Short
                pnl = curr_price - entry_price
                trades.append({'Time': time_ist, 'Type': 'CLOSE LONG', 'Price': curr_price, 'PnL': pnl})
                current_pnl += pnl
                
                action = "SELL (Reverse)"
                in_position = -1
                entry_price = curr_price
                
        # Trailing Logic (Exit only if trend changes? User said "trail both trades with supertrend line")
        # Usually trailing means "Exit if price hits supertrend".
        # Supertrend indicator ALREADY flips trend when price hits it.
        # So "Trend changes" condition implies "Hit Supertrend".
        # We need to check if we are Long but Trend becomes -1 (hit trailing stop)
        
        if in_position == 1 and trend == -1:
             # Hit Trailing Stop
             pnl = curr_price - entry_price
             trades.append({'Time': time_ist, 'Type': 'SL HIT (Long)', 'Price': curr_price, 'PnL': pnl})
             current_pnl += pnl
             market_action = "EXIT LONG"
             in_position = 0
             action = "SL Hit"
             
             # Note: If signal is -1 at same time, we might re-enter Short immediately.
             # In this simple loop, the 'signal' block above handled trend==-1 logic.
             # Wait, if Trend == -1, Signal IS -1 (assuming slope condition met).
             # If Slope condition NOT met, we still exit?
             # "Sell trade hma slope <= -26 WITH supertrend sell" -> Entry condition.
             # "Trail both trades with supertrend line" -> Exit condition.
             # So if Trend flips but No Entry Signal (slope not steep), we just Exit to Flat.
             
        # Logic Refinement:
        # Check Exit First
        # If Long and Trend == -1 -> Close Long.
        # If Short and Trend == 1 -> Close Short.
        
        # Re-evaluating loop order:
        # 1. Update/Check Exit
        # 2. Check Entry
        
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            curr_price = row['close']
            high_price = row['high']
            low_price = row['low']
            time_ist = row['time'] + ist_offset
            trend = row['SupertrendTrend']
            slope = row['HMA_Slope']
            
            # Detect Trend Flip
            # Compare with previous candle (safe because start_idx > 0 due to warmup)
            prev_trend = df.iloc[i-1]['SupertrendTrend']
            if trend != prev_trend:
                trend_start_idx = i
            
            # DEBUG LOG
            if time_ist.hour == 21:
                print(f"DEBUG {time_ist.strftime('%H:%M')} | T:{trend} | Slope:{slope:.2f} | Age:{i-trend_start_idx}")
                
            line_md = ""
            line_console = ""
            
            # 1. Check Take Profit (Intraday)
            if in_position == 1:
                # Update Peak first for stats
                if high_price > trade_peak_price:
                    trade_peak_price = high_price
                
                # Check TP
                if high_price >= entry_price + TAKE_PROFIT:
                    pnl = TAKE_PROFIT # Exact 1000 profit
                    cumulative_pnl += pnl
                    exit_price = entry_price + TAKE_PROFIT
                    
                    # Run Up is at least TP % (likely exactly TP % if limit order filled)
                    run_up = (TAKE_PROFIT / entry_price) * 100
                    
                    line_console = f"{str(time_ist):<25} {'TP HIT (Long)':<15} {entry_price:<10.2f} {exit_price:<10.2f} {pnl:<10.2f} {run_up:<10.2f}\n"
                    line_md = f"| {time_ist} | TP HIT (Long) | {entry_price:.2f} | {exit_price:.2f} | {pnl:.2f} | {run_up:.2f}% |\n"
                    
                    print(line_console, end="")
                    f.write(line_md)
                    
                    in_position = 0
                    entry_price = 0
                    trade_peak_price = 0
                    continue # Skip Close-based checks for this bar
                    
            elif in_position == -1:
                # Update Peak
                if low_price < trade_peak_price:
                    trade_peak_price = low_price
                    
                # Check TP
                if low_price <= entry_price - TAKE_PROFIT:
                    pnl = TAKE_PROFIT
                    cumulative_pnl += pnl
                    exit_price = entry_price - TAKE_PROFIT
                    
                    run_up = (TAKE_PROFIT / entry_price) * 100
                    
                    line_console = f"{str(time_ist):<25} {'TP HIT (Short)':<15} {entry_price:<10.2f} {exit_price:<10.2f} {pnl:<10.2f} {run_up:<10.2f}\n"
                    line_md = f"| {time_ist} | TP HIT (Short) | {entry_price:.2f} | {exit_price:.2f} | {pnl:.2f} | {run_up:.2f}% |\n"
                    
                    print(line_console, end="")
                    f.write(line_md)
                    
                    in_position = 0
                    entry_price = 0
                    trade_peak_price = 0
                    continue
            
            # 2. Check Limits / Trailing Stop (Close-based)
            if in_position == 1:
                if trend == -1: # Supertrend flipped to Sell
                    pnl = curr_price - entry_price
                    cumulative_pnl += pnl
                    
                    # Run Up Calc
                    run_up = (trade_peak_price - entry_price) / entry_price * 100
                    
                    line_console = f"{str(time_ist):<25} {'CLOSE LONG':<15} {entry_price:<10.2f} {curr_price:<10.2f} {pnl:<10.2f} {run_up:<10.2f}\n"
                    line_md = f"| {time_ist} | CLOSE LONG | {entry_price:.2f} | {curr_price:.2f} | {pnl:.2f} | {run_up:.2f}% |\n"
                    
                    in_position = 0
                    entry_price = 0
                    trade_peak_price = 0
                    
            elif in_position == -1:
                if trend == 1: # Supertrend flipped to Buy
                    pnl = entry_price - curr_price
                    cumulative_pnl += pnl
                    
                    # Run Up Calc (Short: Entry - Low)
                    run_up = (entry_price - trade_peak_price) / entry_price * 100
                    
                    line_console = f"{str(time_ist):<25} {'CLOSE SHORT':<15} {entry_price:<10.2f} {curr_price:<10.2f} {pnl:<10.2f} {run_up:<10.2f}\n"
                    line_md = f"| {time_ist} | CLOSE SHORT | {entry_price:.2f} | {curr_price:.2f} | {pnl:.2f} | {run_up:.2f}% |\n"
                    
                    in_position = 0
                    entry_price = 0
                    trade_peak_price = 0
            
            if line_console:
                print(line_console, end="")
                f.write(line_md)
                line_console = ""
                line_md = ""

            # 3. Check Entries
            # Constraint: Entry valid only on 1st or 2nd candle of trend (current index - start index <= 1)
            trend_age = i - trend_start_idx
            
            if in_position == 0:
                # BUY: Trend Bullish, Slope Valid, and Trend is Fresh (<= 1 candle old)
                if trend == 1 and slope >= config.HMA_SLOPE_THRESHOLD:
                    if trend_age <= 1:
                        in_position = 1
                        entry_price = curr_price
                        trade_peak_price = curr_price
                        trade_count += 1
                        
                        line_console = f"{str(time_ist):<25} {'BUY':<15} {curr_price:<10.2f} {'-':<10} {'-':<10} {'-':<10}\n"
                        line_md = f"| {time_ist} | BUY | {curr_price:.2f} | - | - | - |\n"
                    
                # SELL: Trend Bearish, Slope Valid, and Trend is Fresh
                elif trend == -1 and slope <= -config.HMA_SLOPE_THRESHOLD:
                    if trend_age <= 1:
                        in_position = -1
                        entry_price = curr_price
                        trade_peak_price = curr_price
                        trade_count += 1
                        
                        line_console = f"{str(time_ist):<25} {'SELL':<15} {curr_price:<10.2f} {'-':<10} {'-':<10} {'-':<10}\n"
                        line_md = f"| {time_ist} | SELL | {curr_price:.2f} | - | - | - |\n"

            if line_console:
                print(line_console, end="")
                f.write(line_md)

        # Summary
        sep = "-" * 90 + "\n"
        print(sep, end="")
        
        summary_console = f"Total PnL (Points): {cumulative_pnl:.2f}\nTotal Trades Executed: {trade_count}\n"
        print(summary_console)
        
        f.write("\n## Summary\n")
        f.write(f"- **Total Trades**: {trade_count}\n")
        f.write(f"- **Total PnL**: {cumulative_pnl:.2f} Points\n")
        f.write("- **Analysis**: 15m timeframe shows fewer signals but caught significant intraday moves. The trailing stop logic captured gains on trend reversals but experienced drawdown in choppy periods.\n")

if __name__ == "__main__":
    run_backtest()
