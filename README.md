# XtremeBot - Institutional Live Monitor

**XtremeBot** is a high-precision trading bot and live monitoring dashboard designed for **Delta Exchange**. It specializes in trend following strategies on **BTCUSD**, **ETHUSD**, and **SOLUSD** using advanced HMA Slope and Supertrend indicators.

![XtremeBot Dashboard](https://via.placeholder.com/800x400?text=Dashboard+Preview) 
*(Replace with actual screenshot if available)*

## 🚀 Features

*   **Live Dashboard**: 
    *   Real-time Buy/Sell signals.
    *   **Dark/Light Mode** tailored for day/night trading.
    *   "Calm" aesthetic with Slate/Teal/Rose palette.
    *   Live PnL tracking of active positions.
    *   Historical trade log (Last 48 hours).
*   **Advanced Logic**:
    *   **Slope-Based Filtering**: Normalized slope calculation guarantees consistent signals across assets (BTC vs SOL).
    *   **Supertrend Trend Following**: Rides major trends while filtering chop.
    *   **Dynamic Sensitivity**: Calibrated to capture 0.016% moves while ignoring noise.
*   **Backtesting Engine**:
    *   Built-in `backtest.py` to verify strategies against historical data.
    *   Detailed HTML/Markdown reports.

## 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/gorasashivakumar-coder/delta_XtremeBot.git
    cd delta_XtremeBot
    ```

2.  **Install Dependencies**
    Ensure you have Python 3.8+ installed.
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  Open `config.py` in your editor.
2.  Set your Delta Exchange API Credentials:
    ```python
    API_KEY = "your_api_key_here"
    API_SECRET = "your_api_secret_here"
    ```
3.  Adjust Trading Settings (Optional):
    *   `TAKE_PROFIT`: Target profit points (Default: 30).
    *   `SLOPE_SCALING_FACTOR`: Sensitivity of slope signal (Default: 3000).

## 🖥️ Usage

### 1. Run the Live Dashboard (Recommended)
This starts the Flask server which calculates signals and hosts the web interface.
```bash
python server.py
```
*   **Access the Dashboard**: Open your browser and go to `http://localhost:5000`.
*   **Features**:
    *   Auto-refreshes every 2 seconds.
    *   Toggle Light/Dark mode with the icon in the header.

### 2. Run the Trading Bot (Headless)
To run the automated trading logic without the UI:
```bash
python bot.py
```

### 3. Run Backtests
To verify the strategy on historical data:
```bash
python backtest.py
```
*   Results will be saved to `backtest_report.md` and printed to the console.

## 📊 Strategy Details

*   **Timeframe**: 15 Minutes.
*   **Indicators**:
    *   **Hull Moving Average (HMA)**: Period 31.
    *   **Supertrend**: Period 10, Multiplier 3.
    *   **HMA Slope**: Normalized Percentage Slope (> 26 degrees entry).
*   **Entry Logic**:
    *   **Long**: Supertrend Bullish + HMA Slope > 26°.
    *   **Short**: Supertrend Bearish + HMA Slope < -26°.
*   **Exist Logic**:
    *   **Take Profit**: Fixed points (Configurable).
    *   **Trailing Stop**: Supertrend flip.

## 🤝 Contributing

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---
*Built for Alpha.*
