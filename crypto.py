import ccxt
import pandas as pd

# Initialize a public exchange instance
exchange = ccxt.binance({
    'enableRateLimit': True,
})

# A list of coins to scan automatically
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'BNB/USDT']
TIMEFRAME = '15m'
FAST_SMA = 10
SLOW_SMA = 30
INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.001

# Risk Management & Filters
STOP_LOSS_PCT = 0.01
TAKE_PROFIT_PCT = 0.02
USE_VOLUME_FILTER = True
VOL_PERIOD = 20


def run_single_backtest(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=1000)
    except Exception as e:
        print(f"Could not fetch data for {symbol}: {e}")
        return None

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Indicators
    df['fast_sma'] = df['close'].rolling(window=FAST_SMA).mean()
    df['slow_sma'] = df['close'].rolling(window=SLOW_SMA).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['vol_sma'] = df['volume'].rolling(window=VOL_PERIOD).mean()

    df = df.dropna().reset_index(drop=True)

    cash = INITIAL_CAPITAL
    crypto_held = 0.0
    in_position = False
    entry_price = 0.0
    trades_count = 0

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        price = curr['close']

        if in_position:
            stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
            take_profit_price = entry_price * (1 + TAKE_PROFIT_PCT)

            exit_reason = None
            exit_price = price

            if curr['low'] <= stop_loss_price:
                exit_reason = "STOP-LOSS"
                exit_price = stop_loss_price
            elif curr['high'] >= take_profit_price:
                exit_reason = "TAKE-PROFIT"
                exit_price = take_profit_price
            elif prev['fast_sma'] >= prev['slow_sma'] and curr['fast_sma'] < curr['slow_sma']:
                exit_reason = "SMA SIGNAL"
                exit_price = price

            if exit_reason:
                cash = (crypto_held * exit_price) * (1 - FEE_RATE)
                crypto_held = 0.0
                in_position = False
                trades_count += 1

        if not in_position:
            if prev['fast_sma'] <= prev['slow_sma'] and curr['fast_sma'] > curr['slow_sma']:
                if curr['rsi'] < 70:
                    volume_condition_met = True
                    if USE_VOLUME_FILTER:
                        if curr['volume'] <= curr['vol_sma']:
                            volume_condition_met = False

                    if volume_condition_met:
                        amount_to_buy = (cash / price) * (1 - FEE_RATE)
                        crypto_held += amount_to_buy
                        cash = 0.0
                        in_position = True
                        entry_price = price
                        trades_count += 1

    final_price = df.iloc[-1]['close']
    final_portfolio_value = cash + (crypto_held * final_price)
    net_profit = final_portfolio_value - INITIAL_CAPITAL
    return_pct = (net_profit / INITIAL_CAPITAL) * 100

    return {
        'symbol': symbol,
        'final_value': final_portfolio_value,
        'return_pct': return_pct,
        'trades': trades_count
    }


def run_scanner():
    print("Running Multi-Coin Scanner across Binance history...\n")
    results = []

    for symbol in SYMBOLS:
        print(f"Scanning {symbol}...")
        res = run_single_backtest(symbol)
        if res:
            results.append(res)

    # Sort results from highest return to lowest
    results = sorted(results, key=lambda x: x['return_pct'], reverse=True)

    # Print Leaderboard
    print("\n" + "=" * 55)
    print("          QUANTITATIVE STRATEGY LEADERBOARD          ")
    print("=" * 55)
    print(f"{'Symbol':<12} | {'Final Value':<12} | {'Net Return (%)':<15} | {'Trades':<6}")
    print("-" * 55)

    for r in results:
        print(f"{r['symbol']:<12} | ${r['final_value']:<11,.2f} | {r['return_pct']:>6.2f}%          | {r['trades']:<6}")
    print("=" * 55)


if __name__ == "__main__":
    run_scanner()