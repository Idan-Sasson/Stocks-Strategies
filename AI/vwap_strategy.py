import yfinance as yf
import pandas as pd
import numpy as np
from datetime import time

def fetch_data(ticker="QQQ", period="60d", interval="5m"):
    print(f"Fetching data for {ticker} over {period} ({interval} intervals)...")
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if not df.empty:
        df['Date'] = df.index.date
    else:
        print("Error: No data fetched.")
    return df

def calculate_indicators(df):
    print("Calculating Daily VWAP and EMA Momentum...")
    # 1. Typical Price
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VP'] = df['Typical_Price'] * df['Volume']
    
    # 2. Daily VWAP (Anchored per day)
    # Using groupby per day to cumulative sum Volume*Price and Volume
    daily_vp_cum = df.groupby('Date')['VP'].cumsum()
    daily_vol_cum = df.groupby('Date')['Volume'].cumsum()
    
    df['VWAP'] = daily_vp_cum / daily_vol_cum
    
    # 3. Setting a 9-period EMA to proxy trend/momentum
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    
    return df

def run_simulation(df, initial_capital=10000.0, trade_fee=3.0):
    print("Running backtest simulation engine...")
    capital = initial_capital
    position = 0      # 0 = flat, 1 = long, -1 = short
    entry_price = 0.0
    shares = 0
    trades = []
    
    # Strategy Parameters (Risk/Reward)
    stop_loss_pct = 0.005  # 0.5% stop loss distance
    take_profit_pct = 0.010 # 1.0% take profit distance
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        timestamp = df.index[i]
        
        # Determine if it's the end of the trading day (forces exit)
        # Using 15:50 (3:50 PM) as our closing time buffer
        is_end_of_day = (timestamp.time() >= time(15, 50))
        
        # --- EXIT MANAGER ---
        if position != 0:
            exit_reason = None
            exit_price = 0.0
            
            if position == 1: # Long
                sl_price = entry_price * (1 - stop_loss_pct)
                tp_price = entry_price * (1 + take_profit_pct)
                
                if current['Low'] <= sl_price:
                    exit_reason = 'Stop Loss'
                    exit_price = sl_price
                elif current['High'] >= tp_price:
                    exit_reason = 'Take Profit'
                    exit_price = tp_price
                elif is_end_of_day:
                    exit_reason = 'End of Day'
                    exit_price = current['Close']
            
            elif position == -1: # Short
                sl_price = entry_price * (1 + stop_loss_pct)
                tp_price = entry_price * (1 - take_profit_pct)
                
                if current['High'] >= sl_price:
                    exit_reason = 'Stop Loss'
                    exit_price = sl_price
                elif current['Low'] <= tp_price:
                    exit_reason = 'Take Profit'
                    exit_price = tp_price
                elif is_end_of_day:
                    exit_reason = 'End of Day'
                    exit_price = current['Close']
            
            if exit_reason is not None:
                # Execution
                gross_pnl = (exit_price - entry_price) * shares if position == 1 else (entry_price - exit_price) * shares
                net_pnl = gross_pnl - trade_fee # deduct $3 on exit
                
                capital += (entry_price * shares) # Restock equity
                capital += net_pnl # Apply profits/losses
                
                trades.append({
                    'Entry_Time': entry_time,
                    'Exit_Time': timestamp,
                    'Type': 'Long' if position == 1 else 'Short',
                    'Shares': shares,
                    'Entry_Price': entry_price,
                    'Exit_Price': exit_price,
                    'Reason': exit_reason,
                    'Gross_PnL': gross_pnl,
                    'Net_PnL': net_pnl,
                    'Capital': capital
                })
                
                position = 0
                shares = 0
        
        # --- ENTRY MANAGER ---
        if position == 0 and not is_end_of_day:
            if pd.isna(current['VWAP']) or pd.isna(current['EMA_9']):
                continue
            
            trend_up = current['EMA_9'] > current['VWAP']
            trend_down = current['EMA_9'] < current['VWAP']
            
            # Pullback logic:
            # - Must touch / come very close to VWAP (0.2% allowance)
            # - Closed favorably for setup (Green for Long, Red for Short)
            long_cond = (trend_up and 
                        (current['Low'] <= current['VWAP'] * 1.002) and 
                        (current['Close'] > current['VWAP']) and 
                        (current['Close'] > current['Open']))
            
            short_cond = (trend_down and 
                         (current['High'] >= current['VWAP'] * 0.998) and 
                         (current['Close'] < current['VWAP']) and 
                         (current['Close'] < current['Open']))
            
            if long_cond:
                position = 1
                entry_price = current['Close']
                shares = int((capital * 0.90) // entry_price) # Dedicate 90%
                if shares > 0:
                    capital -= (entry_price * shares)
                    capital -= trade_fee # deduct $3 on entry
                    entry_time = timestamp
                else:
                    position = 0 # Not enough buying power
                    
            elif short_cond:
                position = -1
                entry_price = current['Close']
                shares = int((capital * 0.90) // entry_price)
                if shares > 0:
                    capital -= (entry_price * shares)
                    capital -= trade_fee # deduct $3 on entry
                    entry_time = timestamp
                else:
                    position = 0
                    
    return pd.DataFrame(trades), capital

def print_metrics(trades_df, initial_capital, final_capital):
    print("\n" + "="*40)
    print("=== VWAP PULLBACK SIMULATION RESULTS ===")
    print("="*40)
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Capital:   ${final_capital:,.2f}")
    total_net_profit = final_capital - initial_capital
    print(f"Total Net PnL:   ${total_net_profit:,.2f} ({(total_net_profit/initial_capital)*100:.2f}%)")
    print(f"Account for 60-day fees included in Net PnL calculation.")
    
    if trades_df.empty:
        print("\nNo trades executed during this timeframe.")
        return
        
    total_trades = len(trades_df)
    wins = trades_df[trades_df['Net_PnL'] > 0]
    losses = trades_df[trades_df['Net_PnL'] <= 0]
    win_rate = (len(wins) / total_trades) * 100
    
    print(f"Total Trades:    {total_trades}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"Average Win:     ${wins['Net_PnL'].mean():.2f}" if not wins.empty else "Average Win:     $0.00")
    print(f"Average Loss:    ${losses['Net_PnL'].mean():.2f}" if not losses.empty else "Average Loss:    $0.00")
    
    print("\n=== RECENT 5 TRADES ===")
    print(trades_df[['Exit_Time', 'Type', 'Reason', 'Gross_PnL', 'Net_PnL']].tail(5).to_string(index=False))

if __name__ == "__main__":
    tested_ticker = "QQQ" # Testing on a highly liquid ETF
    initial_cap = 10000.0
    
    data_frame = fetch_data(tested_ticker)
    data_frame = calculate_indicators(data_frame)
    trades_df, final_cap = run_simulation(data_frame, initial_capital=initial_cap, trade_fee=3.0)
    
    print_metrics(trades_df, initial_cap, final_cap)
