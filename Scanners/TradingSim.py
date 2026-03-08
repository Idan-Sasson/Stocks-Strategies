import numpy as np
import pandas as pd
from helpers import filter_tickers

class TradingSim:
    def __init__(self, df):
        self.df = df

    def get_next_trading_day(self, date):
        future_dates = self.df[self.df.index >= date].index
        if not future_dates.empty:
            return future_dates[0]
        return None

    def simulate_exit_after(self, ticker, entry, close_after):
        entry = self.get_next_trading_day(entry)
        if isinstance(close_after, str):
            close = self.get_next_trading_day(entry + pd.Timedelta(days=close_after))
        else:
            close = close_after
        buy_price = self.df['Close', ticker].loc[entry]
        sell_price = self.df['Close', ticker].loc[close]
        return float(((sell_price - buy_price) / buy_price))

    def simulate_exit_rsi(self, ticker, entry, rsi_threshold):
        close_prices = self.df['Close']  # 1. Isolate Close prices (returns a DataFrame with dates as index and tickers as columns)
        delta = close_prices.diff()  # 2. Calculate daily price changes
        
        # 3. Separate the gains and losses
        gains = delta.clip(lower=0)  
        losses = -1 * delta.clip(upper=0)
        
        # 4. Calculate the moving averages of gains and losses
        # Wilder's original RSI uses an alpha of 1/14. In pandas, com=window-1 achieves this.
        window = 14
        avg_gains = gains.ewm(com=window - 1, min_periods=window).mean()
        avg_losses = losses.ewm(com=window - 1, min_periods=window).mean()
        rs = avg_gains / avg_losses  # 5. Calculate Relative Strength (RS)
        rsi = 100 - (100 / (1 + rs))  # 6. Calculate the RSI
        return rsi

    def optimizer_exit_after(self, entry, tickers=None):
        optimize_df = self.df
        if tickers:
            optimize_df = filter_tickers(self.df, tickers)
        entry = self.get_next_trading_day(entry)
        if not entry:
            return None
        baseline = optimize_df["Close"].loc[entry]
        returns = ((optimize_df["Close"] / baseline) - 1) * 100
        returns = returns.loc[returns.index >= entry].copy()
        returns.reset_index(drop=True, inplace=True)
        # returns.loc[self.df.index < entry] = np.nan
        # returns.columns = pd.MultiIndex.from_product([['Returns'], returns.columns])
        return returns, returns.drop(columns=["QQQ", "SPY"], errors="ignore").mean(axis=1)
