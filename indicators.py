import pandas as pd
import numpy as np
import math

def calculate_hma(series, period):
    """
    Calculates Hull Moving Average (HMA).
    Formula: HMA = WMA(2 * WMA(n/2) - WMA(n)), sqrt(n))
    """
    wma_half = series.rolling(window=int(period / 2)).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    wma_full = series.rolling(window=period).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    
    raw_hma = 2 * wma_half - wma_full
    sqrt_period = int(math.sqrt(period))
    
    hma = raw_hma.rolling(window=sqrt_period).apply(lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum(), raw=True)
    return hma

def calculate_supertrend(df, period=10, multiplier=3):
    """
    Calculates Supertrend indicator.
    Returns a DataFrame with 'Supertrend', 'SupertrendTrend' (1 for Bullish, -1 for Bearish).
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Calculate ATR
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
    atr = tr.ewm(alpha=1/period).mean()
    
    # Calculate Basic Upper and Lower Bands
    hl2 = (high + low) / 2
    basic_upperband = hl2 + (multiplier * atr)
    basic_lowerband = hl2 - (multiplier * atr)
    
    # Initialize lists for Final Bands and Trend
    final_upperband = [0.0] * len(df)
    final_lowerband = [0.0] * len(df)
    supertrend = [0.0] * len(df)
    # 1 for Bullish (Buy), -1 for Bearish (Sell)
    trend = [1] * len(df) 
    
    for i in range(1, len(df)):
        # Final Upper Band
        if basic_upperband.iloc[i] < final_upperband[i-1] or close.iloc[i-1] > final_upperband[i-1]:
            final_upperband[i] = basic_upperband.iloc[i]
        else:
            final_upperband[i] = final_upperband[i-1]
            
        # Final Lower Band
        if basic_lowerband.iloc[i] > final_lowerband[i-1] or close.iloc[i-1] < final_lowerband[i-1]:
            final_lowerband[i] = basic_lowerband.iloc[i]
        else:
            final_lowerband[i] = final_lowerband[i-1]
            
        # Trend
        if trend[i-1] == 1: # Previous trend was Up
            if close.iloc[i] <= final_lowerband[i]:
                trend[i] = -1
            else:
                trend[i] = 1
        else: # Previous trend was Down
            if close.iloc[i] >= final_upperband[i]:
                trend[i] = 1
            else:
                trend[i] = -1
        
        # Supertrend Value
        if trend[i] == 1:
            supertrend[i] = final_lowerband[i]
        else:
            supertrend[i] = final_upperband[i]
            
    df['Supertrend'] = supertrend
    df['SupertrendTrend'] = trend
    
    return df

def calculate_slope_degrees(series, scaling_factor=1.0):
    """
    Calculates the slope in degrees.
    formula: degrees(atan(pct_change * scaling))
    """
    # Percentage Change from previous bar
    diff = series.pct_change() 
    
    # We apply a scaling factor because percentage is small (0.01 = 1%).
    # We want 0.1% move (~0.001) to look significant.
    # A factor of 2000 makes 0.05% move roughly 45 degrees.
    slopes = diff.apply(lambda x: math.degrees(math.atan(x * scaling_factor)))
    
    return slopes
