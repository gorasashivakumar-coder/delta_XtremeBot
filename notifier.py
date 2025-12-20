import requests
import logging
import config

logger = logging.getLogger(__name__)

def send_telegram_message(message):
    """
    Sends a message to the configured Telegram chat.
    """
    if not config.TELEGRAM_ENABLED:
        return

    token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if not token or "YOUR_" in token:
        logger.warning("Telegram token not configured.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        logger.error(f"Telegram connection error: {e}")

def send_startup_report(history_data, active_positions=None):
    """
    Formats and sends a startup report with past trades and current status.
    history_data: dict { symbol: { 'trades': [], 'current': { 'trend', 'slope', 'price' } } }
    active_positions: list of dicts { 'symbol', 'size', 'entry_price', 'pnl' }
    """
    if not config.TELEGRAM_ENABLED: return
    
    msg = ["🤖 **Bot Started & Connected**\n"]
    
    # 1. Active Positions (Priority)
    if active_positions:
        msg.append("🟢 **Active Exchange Positions:**")
        for pos in active_positions:
            side = "LONG" if pos['size'] > 0 else "SHORT"
            line = f"{pos['symbol']}: {side} {abs(pos['size'])} @ ${pos['entry_price']} (uPnL: {pos['pnl']})"
            msg.append(line)
        msg.append("") # Spacer
    else:
        msg.append("⚪ **No Active Positions on Exchange**\n")
    
    msg.append("📜 **Recent History (Last 24h):**")
    for symbol, data in history_data.items():
        trades = data.get('trades', [])
        if not trades:
            line = f"{symbol}: No trades"
        else:
            wins = len([t for t in trades if t['pnl'] > 0])
            losses = len([t for t in trades if t['pnl'] <= 0])
            total_pnl = sum(t['pnl'] for t in trades)
            line = f"{symbol}: {wins}W/{losses}L (PnL: {total_pnl:+.1f})"
        msg.append(line)
    
    msg.append("\n📊 **Current Market State:**")
    for symbol, data in history_data.items():
        curr = data.get('current', {})
        slope = curr.get('slope', 0)
        thresh = curr.get('threshold', 0)
        trend = "BULL" if curr.get('trend') == 1 else "BEAR"
        price = curr.get('price', 0)
        msg.append(f"{symbol}: {trend} @ {price} (Slope: {slope:.1f}/{thresh})")
        
    msg.append("\n✅ **Live Signals are ACTIVE**")
    
    final_msg = "\n".join(msg)
    send_telegram_message(final_msg)
