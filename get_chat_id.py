import requests
import config
import time

def get_chat_id():
    token = config.TELEGRAM_BOT_TOKEN
    if not token or "YOUR_" in token:
        print("Error: Please put your valid Bot Token in config.py first.")
        return

    print(f"Checking for messages for Bot Token: {token[:10]}...")
    
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, timeout=10).json()
        
        if res.get("ok"):
            results = res.get("result", [])
            if not results:
                print("\n[INFO] No messages found!")
                print("1. Open Telegram and search for your bot.")
                print("2. Click 'Start' or send a message (e.g., 'Hello') to the bot.")
                print("3. Run this script again.")
            else:
                # Get the most recent message
                last_msg = results[-1]
                chat_id = last_msg["message"]["chat"]["id"]
                username = last_msg["message"]["chat"].get("username", "Unknown")
                type = last_msg["message"]["chat"]["type"]
                
                print("\nSUCCESS! Found Chat ID.")
                print("-" * 30)
                print(f"Chat ID: {chat_id}")
                print(f"Type: {type}")
                print(f"User: @{username}")
                print("-" * 30)
                print("Copy this Chat ID and paste it into config.py")
        else:
            print(f"Error from Telegram API: {res}")
            
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    get_chat_id()
