import yfinance as yf
import pandas as pd
from datetime import time

def fetch_data(ticker="QQQ", period="60d", interval="5m"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    if not df.empty: df['Date'] = df.index.date
    return df

def calculate_indicators(df):
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
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
                if current['Low'] <= sl_price: exit_reason, exit_price = 'Stop Loss', sl_price
                elif current['High'] >= tp_price: exit_reason, exit_price = 'Take Profit', tp_price
                elif current['MACD'] < current['Signal']: exit_reason, exit_price = 'Signal Reversal', current['Close']
                elif is_end_of_day: exit_reason, exit_price = 'End of Day', current['Close']
            
            elif position == -1:
                sl_price = entry_price * (1 + stop_loss_pct)
                tp_price = entry_price * (1 - take_profit_pct)
                if current['High'] >= sl_price: exit_reason, exit_price = 'Stop Loss', sl_price
                elif current['Low'] <= tp_price: exit_reason, exit_price = 'Take Profit', tp_price
                elif current['MACD'] > current['Signal']: exit_reason, exit_price = 'Signal Reversal', current['Close']
                elif is_end_of_day: exit_reason, exit_price = 'End of Day', current['Close']
            
            if exit_reason is not None:
                gross_pnl = (exit_price - entry_price) * shares if position == 1 else (entry_price - exit_price) * shares
                net_pnl = gross_pnl - trade_fee 
                capital += (entry_price * shares) + net_pnl
                trades.append({'Exit_Time': timestamp, 'Type': 'Long' if position == 1 else 'Short', 'Reason': exit_reason, 'Net_PnL': net_pnl})
                position, shares = 0, 0
        
        if position == 0 and not is_end_of_day:
            if pd.isna(current['Signal']): continue
            
            cross_up = prev['MACD'] <= prev['Signal'] and current['MACD'] > current['Signal']
            cross_down = prev['MACD'] >= prev['Signal'] and current['MACD'] < current['Signal']
            
            if cross_up: position = 1
            elif cross_down: position = -1
                
            if position != 0:
                entry_price = current['Close']
                shares = int((capital * 0.90) // entry_price)
                if shares > 0: capital -= (entry_price * shares) + trade_fee
                else: position = 0
                    
    return pd.DataFrame(trades), capital

if __name__ == "__main__":
    df = fetch_data("QQQ")
    trades_df, final_cap = run_simulation(calculate_indicators(df))
    print(f"MACD Trend - Total Trades: {len(trades_df)}, Final Capital: ${final_cap:.2f}, Net PnL: ${final_cap-10000:.2f}")
