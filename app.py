import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Crypto Quant Backtester", page_icon="📈", layout="wide")

st.title("📈 Quantitative Crypto Backtesting Dashboard")
st.markdown("Test professional trading strategies live on Kraken data with detailed trade logging!")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Strategy Parameters")

exchange = ccxt.kraken({'enableRateLimit': True})
symbol = st.sidebar.selectbox("Select Asset", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"], index=0)
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=0)

strategy_choice = st.sidebar.selectbox(
    "Trading Strategy",
    ["SMA Crossover + RSI", "Bollinger Band Bounce"]
)

if strategy_choice == "SMA Crossover + RSI":
    fast_sma = st.sidebar.slider("Fast SMA Period", min_value=5, max_value=20, value=10)
    slow_sma = st.sidebar.slider("Slow SMA Period", min_value=21, max_value=60, value=30)
    rsi_limit = st.sidebar.slider("Max RSI Entry Filter", min_value=50, max_value=90, value=70)
else:
    bb_period = st.sidebar.slider("Bollinger Period", min_value=10, max_value=50, value=20)
    bb_std = st.sidebar.slider("Standard Deviations", min_value=1.0, max_value=3.0, value=2.0, step=0.1)

initial_capital = st.sidebar.number_input("Starting Capital ($)", value=1000.0, step=100.0)
fee_rate = 0.001  # 0.1% exchange fee

# --- RUN BACKTEST BUTTON ---
if st.sidebar.button("Run Backtest 🚀"):
    with st.spinner(f"Fetching historical data for {symbol} from Kraken..."):
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=1000)

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # --- INDICATORS ---
        if strategy_choice == "SMA Crossover + RSI":
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
        else:
            df['bb_mid'] = df['close'].rolling(window=bb_period).mean()
            rolling_std = df['close'].rolling(window=bb_period).std()
            df['bb_upper'] = df['bb_mid'] + (bb_std * rolling_std)
            df['bb_lower'] = df['bb_mid'] - (bb_std * rolling_std)

        df = df.dropna().reset_index(drop=True)

        cash = initial_capital
        crypto_held = 0.0
        in_position = False
        entry_price = 0.0
        entry_time = None
        trades_count = 0
        winning_trades = 0
        portfolio_values = []
        benchmark_values = []
        trades_history = []

        first_price = df.iloc[0]['close']

        for i in range(1, len(df)):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            price = curr['close']

            # Portfolio & Benchmark Tracking
            current_portfolio_val = cash + (crypto_held * price)
            portfolio_values.append(current_portfolio_val)

            benchmark_val = initial_capital * (price / first_price)
            benchmark_values.append(benchmark_val)

            # Exit Logic
            if in_position:
                stop_loss = entry_price * 0.98
                take_profit = entry_price * 1.04
                exit_reason = None
                exit_price = price

                if curr['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif curr['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
                elif strategy_choice == "SMA Crossover + RSI":
                    if prev['fast_sma'] >= prev['slow_sma'] and curr['fast_sma'] < curr['slow_sma']:
                        exit_reason = "SMA"
                else:  # Bollinger Band Exit (reach middle band)
                    if price >= curr['bb_mid']:
                        exit_reason = "BB_MID"

                if exit_reason:
                    cash = (crypto_held * exit_price) * (1 - fee_rate)
                    pnl = (exit_price - entry_price) * crypto_held
                    return_pct_trade = ((exit_price - entry_price) / entry_price) * 100

                    if exit_price > entry_price:
                        winning_trades += 1

                    trades_count += 1
                    trades_history.append({
                        "Trade #": trades_count,
                        "Entry Time": entry_time,
                        "Exit Time": curr['timestamp'],
                        "Entry Price": round(entry_price, 2),
                        "Exit Price": round(exit_price, 2),
                        "Profit/Loss ($)": round(pnl, 2),
                        "Return (%)": round(return_pct_trade, 2),
                        "Reason": exit_reason
                    })

                    crypto_held = 0.0
                    in_position = False

            # Entry Logic
            if not in_position:
                if strategy_choice == "SMA Crossover + RSI":
                    if prev['fast_sma'] <= prev['slow_sma'] and curr['fast_sma'] > curr['slow_sma']:
                        if curr['rsi'] < rsi_limit and curr['volume'] > curr['vol_sma']:
                            amount_to_buy = (cash / price) * (1 - fee_rate)
                            crypto_held += amount_to_buy
                            cash = 0.0
                            in_position = True
                            entry_price = price
                            entry_time = curr['timestamp']
                else:  # Bollinger Band Entry (buy when price drops below lower band)
                    if prev['close'] >= prev['bb_lower'] and curr['close'] < curr['bb_lower']:
                        amount_to_buy = (cash / price) * (1 - fee_rate)
                        crypto_held += amount_to_buy
                        cash = 0.0
                        in_position = True
                        entry_price = price
                        entry_time = curr['timestamp']

        final_val = cash + (crypto_held * df.iloc[-1]['close'])
        net_profit = final_val - initial_capital
        return_pct = (net_profit / initial_capital) * 100
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

        final_benchmark_val = benchmark_values[-1]
        benchmark_return_pct = ((final_benchmark_val - initial_capital) / initial_capital) * 100

        # Quant Metrics
        p_series = pd.Series(portfolio_values)
        rolling_max = p_series.cummax()
        drawdown = ((p_series - rolling_max) / rolling_max).min() * 100
        returns = p_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24 * 4) if returns.std() > 0 else 0.0

    # --- DISPLAY METRICS ---
    st.success("Backtest Completed Successfully!")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Strategy Final", f"${final_val:,.2f}", f"{return_pct:+.2f}%")
    col2.metric("Buy & Hold Final", f"${final_benchmark_val:,.2f}", f"{benchmark_return_pct:+.2f}%")
    col3.metric("Total Trades", f"{trades_count}")
    col4.metric("Win Rate", f"{win_rate:.1f}%")
    col5.metric("Sharpe Ratio", f"{sharpe:.2f}")

    st.markdown("---")

    # --- PLOT CHART ---
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['timestamp'][1:], portfolio_values, label=f'Strategy ({strategy_choice})', color='green', linewidth=2)
    ax.plot(df['timestamp'][1:], benchmark_values, label='Buy & Hold Benchmark ($)', color='gray', linestyle='--',
            alpha=0.7)

    ax.set_title(f"{symbol} Performance Comparison")
    ax.set_xlabel("Date / Time")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)

    # --- DISPLAY TRADE LOG ---
    st.markdown("---")
    st.subheader("📜 Detailed Trade History")
    if trades_history:
        trades_df = pd.DataFrame(trades_history)
        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("No completed trades were executed during this backtest period.")
else:
    st.info("👈 Select your strategy and parameters in the sidebar, then click **Run Backtest**!")