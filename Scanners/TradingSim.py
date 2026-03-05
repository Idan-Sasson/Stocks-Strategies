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
        close = self.get_next_trading_day(entry + pd.Timedelta(days=close_after))
        buy_price = self.df['Close', ticker].loc[entry]
        sell_price = self.df['Close', ticker].loc[close]
        return float(((sell_price - buy_price) / buy_price))

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
