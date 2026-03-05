import pandas as pd
import numpy as np

class ExitOptimizer:
    """
    A simulator / optimizer specifically focused on finding the best exit parameters
    given a fixed set of entry dates.
    """
    def __init__(self, data: pd.DataFrame, entry_dates: list, initial_capital=10000.0, apply_fees=True, fee_per_order=3.0):
        """
        data: DataFrame containing 'Open', 'High', 'Low', 'Close'
        entry_dates: list of dates (strings or datetimes) indicating when a Long position is taken 
                     (assumes entry at Close price of that date).
        """
        self.data = data.copy()
        # Ensure index is datetime
        if not isinstance(self.data.index, pd.DatetimeIndex):
            self.data.index = pd.to_datetime(self.data.index)
            
        self.entry_dates = pd.to_datetime(entry_dates)
        self.initial_capital = initial_capital
        self.apply_fees = apply_fees
        self.fee_per_order = fee_per_order
        
        # Verify columns exist
        if 'Close' not in self.data.columns:
            raise ValueError("Data must have a 'Close' column")

    def _simulate_trades(self, exit_signals: pd.Series) -> pd.DataFrame:
        """
        Helper method to simulate trades given a boolean Series of exit signals (True where we should exit).
        Assumes entry is made on self.entry_dates and exit is made on the *first* True in exit_signals after entry.
        """
        trades = []
        df = self.data
        
        for entry_date in self.entry_dates:
            # Check if entry date exists in data
            if entry_date not in df.index:
                continue
                
            entry_idx = df.index.get_loc(entry_date)
            # If entry date is the last day, we can't trade
            if entry_idx >= len(df) - 1:
                continue
                
            entry_price = df.iloc[entry_idx]['Close']
            
            # Find the first exit signal AFTER the entry date
            future_exits = exit_signals.iloc[entry_idx + 1:]
            exit_candidates = future_exits[future_exits == True]
            
            if len(exit_candidates) == 0:
                # No exit signal found, exit at the very end of the dataset
                exit_idx = len(df) - 1
                exit_reason = "Dataset End"
            else:
                exit_date = exit_candidates.index[0]
                exit_idx = df.index.get_loc(exit_date)
                exit_reason = "Signal"
                
            exit_price = df.iloc[exit_idx]['Close']
            exit_date = df.index[exit_idx]
            
            # Compute PnL assuming we invest $initial_capital
            shares = self.initial_capital // entry_price
            if shares == 0:
                continue
                
            gross_pnl = (exit_price - entry_price) * shares
            fees = (self.fee_per_order * 2) if self.apply_fees else 0.0
            net_pnl = gross_pnl - fees
            
            days_held = (exit_date - entry_date).days
            
            trades.append({
                'Entry_Date': entry_date,
                'Exit_Date': exit_date,
                'Entry_Price': entry_price,
                'Exit_Price': exit_price,
                'Shares': shares,
                'Days_Held': days_held,
                'Reason': exit_reason,
                'Net_PnL': net_pnl,
                'ROI_Pct': (net_pnl / self.initial_capital) * 100
            })
            
        return pd.DataFrame(trades)

    def optimize_days_held(self, min_days=1, max_days=30, step=1) -> pd.DataFrame:
        """
        Tests exiting a fixed number of trading days after entry.
        Returns a summary DataFrame with performance for each 'hold_days' value.
        """
        results = []
        df = self.data
        
        print(f"Optimizing for 'Days Held' ({min_days} to {max_days})...")
        
        for hold_days in range(min_days, max_days + 1, step):
            trades = []
            
            for entry_date in self.entry_dates:
                if entry_date not in df.index:
                    continue
                    
                entry_idx = df.index.get_loc(entry_date)
                exit_idx = entry_idx + hold_days
                
                if exit_idx >= len(df):
                    exit_idx = len(df) - 1
                    exit_reason = "Dataset End"
                else:
                    exit_reason = f"{hold_days} Days"
                    
                if exit_idx <= entry_idx:
                    continue
                    
                entry_price = df.iloc[entry_idx]['Close']
                exit_price = df.iloc[exit_idx]['Close']
                exit_date = df.index[exit_idx]
                
                shares = self.initial_capital // entry_price
                if shares == 0: continue
                    
                gross_pnl = (exit_price - entry_price) * shares
                fees = (self.fee_per_order * 2) if self.apply_fees else 0.0
                net_pnl = gross_pnl - fees
                
                trades.append({
                    'Net_PnL': net_pnl,
                    'ROI_Pct': (net_pnl / self.initial_capital) * 100
                })
                
            trades_df = pd.DataFrame(trades)
            if not trades_df.empty:
                wins = len(trades_df[trades_df['Net_PnL'] > 0])
                total = len(trades_df)
                win_rate = (wins / total) * 100
                avg_pnl = trades_df['Net_PnL'].mean()
                avg_roi = trades_df['ROI_Pct'].mean()
                total_pnl = trades_df['Net_PnL'].sum()
                
                results.append({
                    'Hold_Days': hold_days,
                    'Total_Trades': total,
                    'Win_Rate_Pct': win_rate,
                    'Avg_PnL': avg_pnl,
                    'Avg_ROI_Pct': avg_roi,
                    'Total_PnL': total_pnl
                })
                
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values('Total_PnL', ascending=False).reset_index(drop=True)
            
        return res_df

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def optimize_rsi_exit(self, rsi_period=14, min_rsi=50, max_rsi=90, step=5) -> pd.DataFrame:
        """
        Tests exiting when RSI crosses above a specific threshold.
        Returns a summary DataFrame with performance for each RSI threshold.
        """
        results = []
        df = self.data.copy()
        
        # Calculate RSI once
        df['RSI'] = self._calculate_rsi(df['Close'], rsi_period)
        
        print(f"Optimizing for 'RSI Exit' threshold ({min_rsi} to {max_rsi})...")
        
        for rsi_thresh in range(min_rsi, max_rsi + 1, step):
            # Create boolean series where RSI > threshold
            exit_signals = df['RSI'] >= rsi_thresh
            
            trades_df = self._simulate_trades(exit_signals)
            
            if not trades_df.empty:
                wins = len(trades_df[trades_df['Net_PnL'] > 0])
                total = len(trades_df)
                win_rate = (wins / total) * 100
                avg_pnl = trades_df['Net_PnL'].mean()
                avg_roi = trades_df['ROI_Pct'].mean()
                total_pnl = trades_df['Net_PnL'].sum()
                avg_days_held = trades_df['Days_Held'].mean()
                
                results.append({
                    'RSI_Exit_Level': rsi_thresh,
                    'Total_Trades': total,
                    'Win_Rate_Pct': win_rate,
                    'Avg_PnL': avg_pnl,
                    'Avg_ROI_Pct': avg_roi,
                    'Avg_Days_Held': avg_days_held,
                    'Total_PnL': total_pnl
                })
                
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values('Total_PnL', ascending=False).reset_index(drop=True)
            
        return res_df
