import yfinance as yf
import pandas as pd
from exit_optimizer import ExitOptimizer
import time

def main():
    ticker = "SPY"
    print(f"Fetching recent data for {ticker}...")
    data = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
    
    # Flatten multiindex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    print(f"Data fetched: {len(data)} rows.")

    # Let's generate some mock entry dates.
    # For instance, let's enter every time RSI(14) crosses below 30
    print("Generating mock entry dates (RSI < 30)...")
    
    # Simple RSI calculation for entry signals
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Get dates where RSI drops below 30
    entry_signals = rsi < 30
    entry_dates = entry_signals[entry_signals].index.tolist()
    
    print(f"Found {len(entry_dates)} entry dates.")
    if len(entry_dates) == 0:
        print("No entry dates found. Let's just pick every 10th day as an entry for testing.")
        entry_dates = data.iloc[::10].index.tolist()
        print(f"Generated {len(entry_dates)} arbitrary entry dates.")

    # Initialize the optimizer
    optimizer = ExitOptimizer(data=data, entry_dates=entry_dates, initial_capital=10000.0)

    # 1. Optimize Days Held
    start = time.time()
    days_results = optimizer.optimize_days_held(min_days=1, max_days=20, step=1)
    print(f"\nTime taken for Days Held optimization: {time.time()-start:.2f}s")
    
    if not days_results.empty:
        print("\n--- Top 5 'Days Held' Exits ---")
        print(days_results.head(5).to_string(index=False))
    else:
        print("No trades executed for 'Days Held' optimization.")

    # 2. Optimize RSI Exit
    start = time.time()
    rsi_results = optimizer.optimize_rsi_exit(rsi_period=14, min_rsi=50, max_rsi=90, step=5)
    print(f"\nTime taken for RSI Exit optimization: {time.time()-start:.2f}s")
    
    if not rsi_results.empty:
        print("\n--- Top 5 'RSI Exit' Thresholds ---")
        print(rsi_results.head(5).to_string(index=False))
    else:
        print("No trades executed for RSI Exit optimization.")

if __name__ == "__main__":
    main()
