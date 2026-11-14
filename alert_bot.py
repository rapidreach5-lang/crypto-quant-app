import ccxt
import time
import requests

# Initialize exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
})

SYMBOL = 'BTC/USDT'
UPPER_TARGET = 100000.0
LOWER_TARGET = 70000.0

# Paste your Discord Webhook URL here
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1571101255894442035/65VQHedWpIHTEhSoOvk_YRWurxDBrfDoHhLGioAQBL2NfDcU39E1ivtFJtu-TVSMZop1"

def send_discord_alert(message):
    """Sends a formatted message to your Discord channel via webhook"""
    payload = {
        "content": message,
        "username": "Crypto Quant Bot"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"Failed to send Discord alert: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to Discord: {e}")


print(f"Monitoring live feed for {SYMBOL} with Discord webhooks active...")

triggered_upper = False
triggered_lower = False

while True:
    try:
        ticker = exchange.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        print(f"[{timestamp}] {SYMBOL} Current Price: ${current_price:,.2f}")

        # Check Upper Target
        if current_price >= UPPER_TARGET and not triggered_upper:
            alert_msg = f"🚀 **UPPER ALERT!** {SYMBOL} hit **${current_price:,.2f}**!"
            print(alert_msg)
            send_discord_alert(alert_msg)
            triggered_upper = True

        # Check Lower Target
        if current_price <= LOWER_TARGET and not triggered_lower:
            alert_msg = f"🚨 **LOWER ALERT!** {SYMBOL} dropped to **${current_price:,.2f}**!"
            print(alert_msg)
            send_discord_alert(alert_msg)
            triggered_lower = True

        time.sleep(15)

    except KeyboardInterrupt:
        print("\nStopping bot.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)