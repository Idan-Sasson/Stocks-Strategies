import pandas as pd
import numpy as np
import time
import csv
import sys
from engine import SimulationEngine
from strategy_swing_composite import SwingCompositeStrategy

def run_batch_test(subset=None, batch_size=200):
    start_time = time.time()
    file_path = 'AllUSData-max-03-03-2026.csv'
    
    print(f"Reading headers from {file_path}...")
    
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            header_0 = next(reader)
            header_1 = next(reader)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return
        
    date_col = header_0[0]
    
    ticker_cols = {}
    for i in range(1, len(header_1)):
        ticker = header_1[i]
        price_type = header_0[i]
        if ticker and 'Unnamed' not in ticker:
            if ticker not in ticker_cols:
                ticker_cols[ticker] = {}
            ticker_cols[ticker][price_type] = i
            
    all_tickers = sorted(list(ticker_cols.keys()))
    if subset is not None:
        all_tickers = all_tickers[:subset]
        
    print(f"Found {len(ticker_cols)} total tickers.")
    if subset:
        print(f"Testing {len(all_tickers)} tickers in batches of {batch_size}...")
    else:
        print(f"Testing ALL tickers in batches of {batch_size}...")

    results = []
    
    engine = SimulationEngine(
        ticker="TEMP",
        initial_capital=10000.0,
        trade_fee=3.0, 
        trade_size_pct=1.0,
        use_sl_tp=False,
        exit_at_eod=False
    )
    
    strategy = SwingCompositeStrategy(rsi_buy=30, rsi_sell=70, use_stoch=False, use_bb=False, use_macd=False)
    
    for i in range(0, len(all_tickers), batch_size):
        batch_tickers = all_tickers[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{len(all_tickers)//batch_size + 1} ({batch_tickers[0]} to {batch_tickers[-1]})...")
        
        idx_to_col = {}
        for t in batch_tickers:
            for pt, idx in ticker_cols[t].items():
                idx_to_col[idx] = (t, pt)
                
        dates = []
        data = {t: {pt: [] for pt in ticker_cols[t].keys()} for t in batch_tickers}
        
        try:
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)
                next(reader)
                for row in reader:
                    if not row: continue
                    dates.append(row[0])
                    for idx, (t, pt) in idx_to_col.items():
                        val = row[idx] if idx < len(row) else ''
                        if val == '':
                            data[t][pt].append(np.nan)
                        else:
                            try:
                                data[t][pt].append(float(val))
                            except ValueError:
                                data[t][pt].append(np.nan)
        except Exception as e:
            print(f"Error reading block: {e}")
            continue
            
        dt_index = pd.to_datetime(dates, format='mixed', errors='coerce')
        
        for ticker in batch_tickers:
            ticker_data = data[ticker]
            ticker_df = pd.DataFrame(ticker_data, index=dt_index)
            ticker_df.dropna(how='all', inplace=True)
            
            if len(ticker_df) < 50:
                continue
                
            cols = {c.lower(): c for c in ticker_df.columns}
            new_cols = {}
            if 'open' in cols: new_cols[cols['open']] = 'Open'
            if 'high' in cols: new_cols[cols['high']] = 'High'
            if 'low' in cols: new_cols[cols['low']] = 'Low'
            if 'close' in cols: new_cols[cols['close']] = 'Close'
            elif 'adj close' in cols: new_cols[cols['adj close']] = 'Close'
            if 'volume' in cols: new_cols[cols['volume']] = 'Volume'
                
            ticker_df = ticker_df.rename(columns=new_cols)
            
            engine.ticker = ticker
            engine.data = ticker_df
            
            try:
                trades_df, final_capital = engine.run(strategy)
            except Exception as e:
                continue
                
            net_pnl = final_capital - engine.initial_capital
            if not trades_df.empty:
                total_trades = len(trades_df)
                wins = len(trades_df[trades_df['Net_PnL'] > 0])
                win_rate = (wins / total_trades) * 100
                avg_days = trades_df['Days_Held'].mean()
            else:
                total_trades = 0
                wins = 0
                win_rate = 0.0
                avg_days = 0.0
                
            results.append({
                'Ticker': ticker,
                'Total_Trades': total_trades,
                'Win_Rate_Pct': win_rate,
                'Net_PnL': net_pnl,
                'Final_Capital': final_capital,
                'Avg_Days_Held': avg_days
            })
                
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values('Net_PnL', ascending=False)
            res_df.to_csv("batch_results.csv", index=False)

    print("\n=== TOP 10 PERFORMING TICKERS ===")
    if len(results) > 0:
        print(res_df.head(10).to_string(index=False))
        print("\n=== BOTTOM 5 PERFORMING TICKERS ===")
        print(res_df.tail(5).to_string(index=False))
    print(f"\nBatch test complete! Results saved to batch_results.csv")
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    subset = None
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            subset = int(sys.argv[1])
            
    if subset is None:
        print("Note: Provide a number like 'python batch_test.py 15' to test a subset.")
        print("Running full batch on ALL 7346 tickers... this will take a long time!")
        run_batch_test(subset=None)
    else:
        run_batch_test(subset=subset)
