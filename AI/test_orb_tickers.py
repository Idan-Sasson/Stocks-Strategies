import strategy_orb

tickers = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META"]

print("=== TESTING ORB ON MULTIPLE TICKERS ===")
for ticker in tickers:
    try:
        df = strategy_orb.fetch_data(ticker)
        if df.empty:
            print(f"{ticker}: No data fetched.")
            continue
        df_indicators = strategy_orb.calculate_indicators(df)
        trades_df, final_cap = strategy_orb.run_simulation(df_indicators)
        print(f"{ticker:>5} | Trades: {len(trades_df):>3} | Net PnL: ${final_cap-10000:>8.2f}")
    except Exception as e:
        print(f"{ticker}: Error - {e}")
