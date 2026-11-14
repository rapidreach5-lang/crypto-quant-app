import ccxt
import pandas as pd
import numpy as np

# Initialize a public exchange instance
exchange = ccxt.binance({
    'enableRateLimit': True,
})

SYMBOL = 'BTC/USDT'  # You can change this to any coin!
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


def run_backtest():
    print(f"Fetching historical 15m data for {SYMBOL} from Binance...")
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=5000)

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
    winning_trades = 0

    # Track portfolio value over time for Max Drawdown and Sharpe Ratio
    portfolio_values = []

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        price = curr['close']

        # Track current portfolio value at each step
        current_portfolio_val = cash + (crypto_held * price)
        portfolio_values.append(current_portfolio_val)

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
                if exit_price > entry_price:
                    winning_trades += 1
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

    # Final portfolio value
    final_price = df.iloc[-1]['close']
    final_portfolio_value = cash + (crypto_held * final_price)
    net_profit = final_portfolio_value - INITIAL_CAPITAL
    return_pct = (net_profit / INITIAL_CAPITAL) * 100
    win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

    # --- CALCULATE PROFESSIONAL QUANT METRICS ---
    portfolio_series = pd.Series(portfolio_values)

    # 1. Max Drawdown Calculation
    rolling_max = portfolio_series.cummax()
    drawdown = (portfolio_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100  # Convert to percentage

    # 2. Sharpe Ratio Calculation (annualized for 15m intervals)
    returns = portfolio_series.pct_change().dropna()
    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365 * 24 * 4) if returns.std() > 0 else 0.0

    # Print Results
    print("\n" + "=" * 50)
    print("      PROFESSIONAL QUANTITATIVE BACKTEST RESULTS     ")
    print("=" * 50)
    print(f"Asset Tested          : {SYMBOL}")
    print(f"Starting Capital      : ${INITIAL_CAPITAL:,.2f}")
    print(f"Final Portfolio Value : ${final_portfolio_value:,.2f}")
    print(f"Net Profit / Loss     : ${net_profit:,.2f} ({return_pct:.2f}%)")
    print(f"Total Trades Executed : {trades_count}")
    print(f"Win Rate              : {win_rate:.1f}%")
    print("-" * 50)
    print(f"ADVANCED QUANT METRICS:")
    print(f"  • Max Drawdown      : {max_drawdown:.2f}%")
    print(f"  • Sharpe Ratio      : {sharpe_ratio:.2f}")
    print("=" * 50)


if __name__ == "__main__":
    run_backtest()