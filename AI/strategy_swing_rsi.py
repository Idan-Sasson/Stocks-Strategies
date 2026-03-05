import pandas as pd

class SwingRSIStrategy:
    def __init__(self, rsi_buy=30, rsi_sell=70):
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell

    def calculate_indicators(self, df):
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def check_exit(self, position, current, prev):
        if position == 1 and current['RSI'] > self.rsi_sell:
            return f'RSI Over {self.rsi_sell} (Exit Long)', current['Close']
        return None, None

    def check_entry(self, current, prev):
        if pd.isna(current['RSI']): 
            return 0
            
        # Buy on extreme pullbacks 
        if current['RSI'] < self.rsi_buy:
            return 1
            
        return 0
