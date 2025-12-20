import config

def scan_trades_for_df(df, symbol):
    """
    Scans the dataframe for historical trades based on strategy logic.
    Returns a list of trade dicts.
    """
    trades = []
    in_position = 0 # 0, 1, -1
    entry_price = 0.0
    entry_time = None
    
    # Pre-calc Trend Age for entire DF
    trend_starts = [0] * len(df)
    current_start = 0
    # Assuming df has 'SupertrendTrend' column
    # Iterate from 1
    for i in range(1, len(df)):
        if df.iloc[i]['SupertrendTrend'] != df.iloc[i-1]['SupertrendTrend']:
            current_start = i
        trend_starts[i] = current_start
        
    # Determine Quantity
    qty = config.QUANTITIES.get(symbol, config.DEFAULT_QUANTITY)
    
    sym_config = config.SYMBOL_CONFIG.get(symbol, {})
    slope_threshold = sym_config.get("slope_threshold", config.HMA_SLOPE_THRESHOLD)

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
            pnl = (curr_price - entry_price) * qty
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
            pnl = (entry_price - curr_price) * qty
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
            if trend == 1 and slope >= slope_threshold and trend_age <= 1:
                in_position = 1
                entry_price = curr_price
                entry_time = time_str
                
            # SELL
            elif trend == -1 and slope <= -slope_threshold and trend_age <= 1:
                in_position = -1
                entry_price = curr_price
                entry_time = time_str
    
    # If still in position, add Open Trade
    if in_position != 0:
        curr_price = df.iloc[-1]['close']
        pnl = ((curr_price - entry_price) if in_position == 1 else (entry_price - curr_price)) * qty
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
