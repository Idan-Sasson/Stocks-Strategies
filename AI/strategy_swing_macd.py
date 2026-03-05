import pandas as pd

class SwingMACDStrategy:
    """
    Swing Trading Strategy: Uses Daily candles.
    Enters Long whenMACD crosses Signal line below 0.
    Enters Short when MACD crosses Signal line above 0.
    """
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def check_exit(self, position, current, prev):
        # Sell when RSI shows deeply overbought
        if position == 1 and current['RSI'] > 70:
            return 'RSI Overbought (Exit Long)', current['Close']
            
        return None, None

    def check_entry(self, current, prev):
        if pd.isna(current['RSI']): 
            return 0
            
        # Buy on extreme pullbacks 
        if current['RSI'] < 30:
            return 1
            
        return 0
