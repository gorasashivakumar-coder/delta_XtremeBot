import numpy as np
import pandas as pd
import math

def old_slope(series, factor=1.0):
    diff = series.diff()
    return diff.apply(lambda x: math.degrees(math.atan(x * factor)))

def new_slope_pct(series, factor=2000.0):
    pct = series.pct_change()
    return pct.apply(lambda x: math.degrees(math.atan(x * factor)))

# Fake Data
# BTC: 90000 -> 90100 (0.11% move, +100 raw)
btc = pd.Series([90000, 90100, 90200])
# SOL: 120 -> 120.15 (0.12% move, +0.15 raw)
sol = pd.Series([120, 120.15, 120.30])

print("--- BTC (90k -> 90.1k) ---")
print(f"Old Slope (F=1): {old_slope(btc).iloc[1]:.2f}")
print(f"New Slope (F=2000): {new_slope_pct(btc).iloc[1]:.2f}")

print("\n--- SOL (120 -> 120.15) ---")
print(f"Old Slope (F=1): {old_slope(sol).iloc[1]:.2f}")
print(f"New Slope (F=2000): {new_slope_pct(sol).iloc[1]:.2f}")

print(f"\nTarget Threshold: 26 degrees.")
