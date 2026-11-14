import ccxt
import pandas as pd
import time
import requests

# Initialize exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
})

SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
FAST_SMA = 10
SLOW_SMA = 30
RSI_LIMIT = 70

# Paste your Discord Webhook URL here
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1571101255894442035/65VQHedWpIHTEhSoOvk_YRWurxDBrfDoHhLGioAQBL2NfDcU39E1ivtFJtu-TVSMZop1"


def send_discord_alert(message):
    """Sends strategy alerts straight to your Discord channel"""
    payload = {
        "content": message,
        "username": "Quant Strategy Bot"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Discord connection error: {e}")


print(f"==================================================")
print(f"  LIVE STRATEGY BOT INITIALIZED FOR {SYMBOL}      ")
print(f"==================================================")
print(f"Monitoring live 15m candles... (Press Ctrl+C to stop)\n")

# Track whether our strategy currently holds a position
in_position = False

while True:
    try:
        # Fetch recent live candles (fetching 100 is plenty to calculate 30-period SMAs)
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # --- CALCULATE INDICATORS (Same logic as backtest.py) ---
        df['fast_sma'] = df['close'].rolling(window=FAST_SMA).mean()
        df['slow_sma'] = df['close'].rolling(window=SLOW_SMA).mean()

        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['vol_sma'] = df['volume'].rolling(window=20).mean()

        # Look at the previous and current candles
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        current_price = curr['close']
        timestamp = pd.to_datetime(curr['timestamp'], unit='ms').strftime('%Y-%m-%d %H:%M:%S')

        print(f"[{timestamp}] {SYMBOL} Price: ${current_price:,.2f} | Position: {in_position}")

        # --- STRATEGY CHECK: BUY SIGNAL ---
        if not in_position:
            # Bullish crossover + RSI filter + Volume filter
            if prev['fast_sma'] <= prev['slow_sma'] and curr['fast_sma'] > curr['slow_sma']:
                if curr['rsi'] < RSI_LIMIT and curr['volume'] > curr['vol_sma']:
                    msg = f"🚀 **LIVE BUY SIGNAL!**\n• Asset: {SYMBOL}\n• Price: **${current_price:,.2f}**\n• Time: {timestamp}"
                    print("\n" + msg + "\n")
                    send_discord_alert(msg)
                    in_position = True

        # --- STRATEGY CHECK: SELL SIGNAL ---
        elif in_position:
            # Bearish crossover exit
            if prev['fast_sma'] >= prev['slow_sma'] and curr['fast_sma'] < curr['slow_sma']:
                msg = f"📉 **LIVE SELL SIGNAL!**\n• Asset: {SYMBOL}\n• Price: **${current_price:,.2f}**\n• Time: {timestamp}"
                print("\n" + msg + "\n")
                send_discord_alert(msg)
                in_position = False

        # Check every 60 seconds to catch candle updates cleanly
        time.sleep(60)

    except KeyboardInterrupt:
        print("\nStopping live strategy bot. Great work!")
        break
    except Exception as e:
        print(f"Error in live loop: {e}. Retrying in 15 seconds...")
        time.sleep(15)