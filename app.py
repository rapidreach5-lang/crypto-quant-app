import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Crypto Quant Backtester", page_icon="📈", layout="wide")

st.title("📈 Quantitative Crypto Backtesting Dashboard")
st.markdown("Test Moving Average crossover strategies with RSI and volume filters live on Binance data!")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Strategy Parameters")

symbol = st.sidebar.selectbox("Select Asset", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"], index=0)T", "BNB/USDT"], index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=0)

fast_sma = st.sidebar.slider("Fast SMA Period", min_value=5, max_value=20, value=10)
slow_sma = st.sidebar.slider("Slow SMA Period", min_value=21, max_value=60, value=30)
rsi_limit = st.sidebar.slider("Max RSI Entry Filter", min_value=50, max_value=90, value=70)

initial_capital = st.sidebar.number_input("Starting Capital ($)", value=1000.0, step=100.0)
fee_rate = 0.001  # 0.1% exchange fee

# --- RUN BACKTEST BUTTON ---
if st.sidebar.button("Run Backtest 🚀"):
    with st.spinner(f"Fetching historical data for {symbol} from Binance..."):


        # To Kraken (supports all your pairs and timeframes):
        exchange = ccxt.kraken({'enableRateLimit': True})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=1000)

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Indicators
        df['fast_sma'] = df['close'].rolling(window=fast_sma).mean()
        df['slow_sma'] = df['close'].rolling(window=slow_sma).mean()

        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['vol_sma'] = df['volume'].rolling(window=20).mean()

        df = df.dropna().reset_index(drop=True)

        cash = initial_capital
        crypto_held = 0.0
        in_position = False
        entry_price = 0.0
        trades_count = 0
        winning_trades = 0
        portfolio_values = []
        trade_signals = []  # For plotting

        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            price = curr['close']

            current_portfolio_val = cash + (crypto_held * price)
            portfolio_values.append(current_portfolio_val)

            if in_position:
                stop_loss = entry_price * 0.99
                take_profit = entry_price * 1.02
                exit_reason = None
                exit_price = price

                if curr['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif curr['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
                elif prev['fast_sma'] >= prev['slow_sma'] and curr['fast_sma'] < curr['slow_sma']:
                    exit_reason = "SMA"

                if exit_reason:
                    cash = (crypto_held * exit_price) * (1 - fee_rate)
                    if exit_price > entry_price:
                        winning_trades += 1
                    crypto_held = 0.0
                    in_position = False
                    trades_count += 1
                    trade_signals.append((curr['timestamp'], exit_price, 'sell'))

            if not in_position:
                if prev['fast_sma'] <= prev['slow_sma'] and curr['fast_sma'] > curr['slow_sma']:
                    if curr['rsi'] < rsi_limit and curr['volume'] > curr['vol_sma']:
                        amount_to_buy = (cash / price) * (1 - fee_rate)
                        crypto_held += amount_to_buy
                        cash = 0.0
                        in_position = True
                        entry_price = price
                        trade_signals.append((curr['timestamp'], price, 'buy'))

        final_val = cash + (crypto_held * df.iloc[-1]['close'])
        net_profit = final_val - initial_capital
        return_pct = (net_profit / initial_capital) * 100
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

        # Quant Metrics
        p_series = pd.Series(portfolio_values)
        rolling_max = p_series.cummax()
        drawdown = ((p_series - rolling_max) / rolling_max).min() * 100
        returns = p_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24 * 4) if returns.std() > 0 else 0.0

    # --- DISPLAY METRICS IN STREAMLIT ---
    st.success("Backtest Completed Successfully!")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Final Portfolio", f"${final_val:,.2f}", f"{return_pct:+.2f}%")
    col2.metric("Total Trades", f"{trades_count}")
    col3.metric("Win Rate", f"{win_rate:.1f}%")
    col4.metric("Sharpe Ratio", f"{sharpe:.2f}")

    st.markdown("---")

    # --- PLOT CHART ---
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['timestamp'], df['close'], label='Price', color='blue', alpha=0.6)
    ax.plot(df['timestamp'], df['fast_sma'], label=f'Fast SMA ({fast_sma})', color='orange', alpha=0.8)
    ax.plot(df['timestamp'], df['slow_sma'], label=f'Slow SMA ({slow_sma})', color='purple', alpha=0.8)

    ax.set_title(f"{symbol} Backtest Performance Chart")
    ax.set_xlabel("Date / Time")
    ax.set_ylabel("Price (USDT)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)
else:
    st.info("👈 Adjust your parameters in the sidebar and click **Run Backtest** to start!")