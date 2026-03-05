import yfinance as yf
import pandas as pd
from datetime import time

class SimulationEngine:
    def __init__(self, ticker='QQQ', initial_capital=10000.0, period='2y', interval='1d', 
                 trade_fee=3.0, trade_size_pct=1.0, stop_loss_pct=0.03, take_profit_pct=0.08,
                 use_sl_tp=True, exit_at_eod=True, end_of_day_exit_time="15:55"):
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.period = period
        self.interval = interval
        self.trade_fee = trade_fee
        self.trade_size_pct = trade_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_sl_tp = use_sl_tp
        self.exit_at_eod = exit_at_eod
        
        # Parse exit time
        if isinstance(end_of_day_exit_time, str):
            self.end_of_day_exit_time = time.fromisoformat(end_of_day_exit_time)
        else:
            self.end_of_day_exit_time = end_of_day_exit_time
            
        self.data = None

    def fetch_data(self):
        print(f"Fetching {self.period} of {self.interval} data for {self.ticker}...")
        self.data = yf.download(self.ticker, period=self.period, interval=self.interval, auto_adjust=True)
        if self.data.empty:
            raise ValueError("No data fetched. Check ticker or internet connection.")
            
        # Flatten MultiIndex columns if necessary
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = self.data.columns.get_level_values(0)
            
        return self.data

    def run(self, strategy):
        if self.data is None:
            self.fetch_data()
            
        # 1. Indicator Calculation
        df = strategy.calculate_indicators(self.data.copy())
        
        capital = self.initial_capital
        position = 0      # 1: Long, -1: Short, 0: Flat
        shares = 0
        entry_price = 0.0
        entry_time = None
        trades = []
        
        # 2. Main Simulation Loop
        for i in range(1, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            timestamp = df.index[i]
            
            # --- EXIT MANAGER ---
            if position != 0:
                exit_reason = None
                exit_price = 0.0
                
                # A. Stop Loss / Take Profit (Standard)
                if self.use_sl_tp:
                    if position == 1:
                        sl_p = entry_price * (1 - self.stop_loss_pct)
                        tp_p = entry_price * (1 + self.take_profit_pct)
                        if current['Low'] <= sl_p: exit_reason, exit_price = 'Stop Loss', sl_p
                        elif current['High'] >= tp_p: exit_reason, exit_price = 'Take Profit', tp_p
                    elif position == -1:
                        sl_p = entry_price * (1 + self.stop_loss_pct)
                        tp_p = entry_price * (1 - self.take_profit_pct)
                        if current['High'] >= sl_p: exit_reason, exit_price = 'Stop Loss', sl_p
                        elif current['Low'] <= tp_p: exit_reason, exit_price = 'Take Profit', tp_p

                # B. End of Day Exit (Day Trading)
                if exit_reason is None and self.exit_at_eod:
                    if hasattr(timestamp, 'time') and timestamp.time() >= self.end_of_day_exit_time:
                        exit_reason, exit_price = 'End of Day', current['Close']

                # C. Strategy Signal Exit
                if exit_reason is None and hasattr(strategy, 'check_exit'):
                    reason, price = strategy.check_exit(position, current, prev)
                    if reason:
                        exit_reason, exit_price = reason, price if price else current['Close']

                # PROCESS EXIT
                if exit_reason:
                    raw_profit = (exit_price - entry_price) * shares if position == 1 else (entry_price - exit_price) * shares
                    net_profit = raw_profit - (self.trade_fee * 2) # Fee on entry + fee on exit
                    capital += net_profit
                    
                    # Calculate duration in days
                    trade_duration = (timestamp - entry_time).days if entry_time else 0
                    
                    trades.append({
                        'Entry_Time': entry_time,
                        'Exit_Time': timestamp,
                        'Type': 'Long' if position == 1 else 'Short',
                        'Entry_Price': entry_price,
                        'Exit_Price': exit_price,
                        'Shares': shares,
                        'Days_Held': trade_duration,
                        'Reason': exit_reason,
                        'Net_PnL': net_profit,
                        'Capital': capital
                    })
                    
                    position, shares = 0, 0
            
            # --- ENTRY MANAGER ---
            if position == 0:
                # Basic EOD safety for Day Trading entries
                can_enter = True
                if self.exit_at_eod and hasattr(timestamp, 'time') and timestamp.time() >= self.end_of_day_exit_time:
                    can_enter = False

                if can_enter:
                    signal = strategy.check_entry(current, prev)
                    if signal != 0:
                        position = signal
                        entry_price = current['Close']
                        entry_time = timestamp
                        shares = int((capital * self.trade_size_pct) // entry_price)
                        if shares <= 0:
                            position = 0 # Out of capital

        # 3. Final Liquidation
        if position != 0:
            last_price = df.iloc[-1]['Close']
            raw_profit = (last_price - entry_price) * shares if position == 1 else (entry_price - last_price) * shares
            net_profit = raw_profit - (self.trade_fee * 2)
            capital += net_profit
            trade_duration = (df.index[-1] - entry_time).days if entry_time else 0
            trades.append({
                'Entry_Time': entry_time,
                'Exit_Time': df.index[-1],
                'Type': 'Long' if position == 1 else 'Short',
                'Entry_Price': entry_price,
                'Exit_Price': last_price,
                'Shares': shares,
                'Days_Held': trade_duration,
                'Reason': 'Simulation Ended',
                'Net_PnL': net_profit,
                'Capital': capital
            })

        return pd.DataFrame(trades), capital

    def print_results(self, trades_df, final_capital, strategy_name):
        print(f"\n--- Results for {strategy_name} ---")
        print(f"Ticker: {self.ticker} | Initial Capital: ${self.initial_capital:.2f}")
        print(f"Trade Size: {self.trade_size_pct*100}% | Fee per order: ${self.trade_fee:.2f}")
        
        if not trades_df.empty:
            total_trades = len(trades_df)
            wins = len(trades_df[trades_df['Net_PnL'] > 0])
            win_rate = (wins / total_trades) * 100
            net_pnl = final_capital - self.initial_capital
            avg_days = trades_df['Days_Held'].mean()
            
            print(f"Total Trades:    {total_trades}")
            print(f"Avg Days Held:   {avg_days:.1f} days")
            print(f"Final Capital:   ${final_capital:.2f}")
            print(f"Net PnL:         ${net_pnl:.2f}")
            print(f"Win Rate:        {win_rate:.2f}%")
        else:
            print("No trades executed.")
        print("-" * 35 + "\n")
