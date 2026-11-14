import ccxt
import pandas as pd
import time
import requests

# Initialize exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
})

# List of coins to watch simultaneously
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'BNB/USDT']
TIMEFRAME = '15m'
FAST_SMA = 10
SLOW_SMA = 30
RSI_LIMIT = 70

# Paste your Discord Webhook URL here
DISCORD_WEBHOOK_URL ="https://discord.com/api/webhooks/1571101255894442035/65VQHedWpIHTEhSoOvk_YRWurxDBrfDoHhLGioAQBL2NfDcU39E1ivtFJtu-TVSMZop1"


def send_discord_alert(message):
    """Sends multi-coin strategy alerts to Discord"""
    payload = {
        "content": message,
        "username": "Quant Multi-Bot"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Discord connection error: {e}")


print("=" * 60)
print("  MULTI-COIN LIVE STRATEGY WATCHDOG INITIALIZED")
print("=" * 60)
print(f"Monitoring coins: {', '.join(SYMBOLS)}")
print("Scanning live candles every 60 seconds... (Press Ctrl+C to stop)\n")

# Dictionary to keep track of active positions for each coin separately
positions = {symbol: False for symbol in SYMBOLS}

while True:
    try:
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp_str}] Scanning market scan cycle...")

        for symbol in SYMBOLS:
            try:
                # Fetch recent live candles for the current symbol
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Calculate Indicators
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

                prev = df.iloc[-2]
                curr = df.iloc[-1]
                current_price = curr['close']
                candle_time = pd.to_datetime(curr['timestamp'], unit='ms').strftime('%H:%M:%S')

                in_pos = positions[symbol]

                # --- BUY SIGNAL CHECK ---
                if not in_pos:
                    if prev['fast_sma'] <= prev['slow_sma'] and curr['fast_sma'] > curr['slow_sma']:
                        if curr['rsi'] < RSI_LIMIT and curr['volume'] > curr['vol_sma']:
                            msg = f"🚀 **MULTI-BOT BUY SIGNAL ({symbol})!**\n• Price: **${current_price:,.2f}**\n• Time: {candle_time}"
                            print(f"\n[SIGNAL] {symbol} BUY at ${current_price:,.2f}\n")
                            send_discord_alert(msg)
                            positions[symbol] = True

                # --- SELL SIGNAL CHECK ---
                elif in_pos:
                    if prev['fast_sma'] >= prev['slow_sma'] and curr['fast_sma'] < curr['slow_sma']:
                        msg = f"📉 **MULTI-BOT SELL SIGNAL ({symbol})!**\n• Price: **${current_price:,.2f}**\n• Time: {candle_time}"
                        print(f"\n[SIGNAL] {symbol} SELL at ${current_price:,.2f}\n")
                        send_discord_alert(msg)
                        positions[symbol] = False

                # Brief pause between coins to respect Binance rate limits
                time.sleep(1)

            except Exception as coin_err:
                print(f"Error scanning {symbol}: {coin_err}")

        # Wait 60 seconds before running the next full market scan
        print(f"Scan complete. Waiting 60 seconds for next check...\n")
        time.sleep(60)

    except KeyboardInterrupt:
        print("\nStopping Multi-Coin Watchdog. Great work!")
        break
    except Exception as e:
        print(f"Error in main loop: {e}. Retrying in 15 seconds...")
        time.sleep(15)