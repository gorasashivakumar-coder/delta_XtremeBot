import indicators
print("Imported indicators.")
try:
    print(indicators.calculate_slope_degrees)
    print("Function found.")
except AttributeError:
    print("Function NOT found.")
    print(dir(indicators))
