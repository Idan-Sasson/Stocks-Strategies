import yfinance as yf
import pandas as pd
from datetime import time

def fetch_data(ticker="QQQ", period="60d", interval="5m"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    if not df.empty: df['Date'] = df.index.date
    return df

def calculate_indicators(df):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    ema_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = ema_gain / ema_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def run_simulation(df, initial_capital=10000.0, trade_fee=3.0):
    capital = initial_capital
    position = 0      
    entry_price = 0.0
    shares = 0
    trades = []
    
    stop_loss_pct = 0.005
    take_profit_pct = 0.010
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        timestamp = df.index[i]
        
        is_end_of_day = (timestamp.time() >= time(15, 50))
        
        if position != 0:
            exit_reason = None
            exit_price = 0.0
            
            if position == 1:
                sl_price = entry_price * (1 - stop_loss_pct)
                tp_price = entry_price * (1 + take_profit_pct)
                if current['Low'] <= sl_price:
                    exit_reason, exit_price = 'Stop Loss', sl_price
                elif current['High'] >= tp_price:
                    exit_reason, exit_price = 'Take Profit', tp_price
                elif current['RSI'] >= 50:
                    exit_reason, exit_price = 'Mean Reverted', current['Close']
                elif is_end_of_day:
                    exit_reason, exit_price = 'End of Day', current['Close']
            
            elif position == -1:
                sl_price = entry_price * (1 + stop_loss_pct)
                tp_price = entry_price * (1 - take_profit_pct)
                if current['High'] >= sl_price:
                    exit_reason, exit_price = 'Stop Loss', sl_price
                elif current['Low'] <= tp_price:
                    exit_reason, exit_price = 'Take Profit', tp_price
                elif current['RSI'] <= 50:
                    exit_reason, exit_price = 'Mean Reverted', current['Close']
                elif is_end_of_day:
                    exit_reason, exit_price = 'End of Day', current['Close']
            
            if exit_reason is not None:
                gross_pnl = (exit_price - entry_price) * shares if position == 1 else (entry_price - exit_price) * shares
                net_pnl = gross_pnl - trade_fee 
                capital += (entry_price * shares) + net_pnl
                trades.append({'Exit_Time': timestamp, 'Type': 'Long' if position == 1 else 'Short', 'Reason': exit_reason, 'Net_PnL': net_pnl})
                position, shares = 0, 0
        
        if position == 0 and not is_end_of_day:
            if pd.isna(current['RSI']): continue
            
            if current['RSI'] < 30 and prev['RSI'] >= 30: # Cross below 30 (Oversold hook)
                position = 1
            elif current['RSI'] > 70 and prev['RSI'] <= 70: # Cross above 70 (Overbought hook)
                position = -1
                
            if position != 0:
                entry_price = current['Close']
                shares = int((capital * 0.90) // entry_price)
                if shares > 0: capital -= (entry_price * shares) + trade_fee
                else: position = 0
                    
    return pd.DataFrame(trades), capital

if __name__ == "__main__":
    df = fetch_data("QQQ")
    trades_df, final_cap = run_simulation(calculate_indicators(df))
    print(f"RSI Reversion - Total Trades: {len(trades_df)}, Final Capital: ${final_cap:.2f}, Net PnL: ${final_cap-10000:.2f}")
