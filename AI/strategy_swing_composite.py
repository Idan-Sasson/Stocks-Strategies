import pandas as pd
import numpy as np

class SwingCompositeStrategy:
    def __init__(self, rsi_buy=30, rsi_sell=70, 
                 use_stoch=False, use_bb=False, use_macd=False):
        """
        A multi-indicator swing strategy that can be configured via optimizer.
        """
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        
        # Indicator toggles
        self.use_stoch = use_stoch
        self.use_bb = use_bb
        self.use_macd = use_macd

    def calculate_indicators(self, df):
        # 1. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 2. Stochastic Oscillator (14, 3, 3)
        low_14 = df['Low'].rolling(14).min()
        high_14 = df['High'].rolling(14).max()
        df['Stoch_K'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
        
        # 3. Bollinger Bands (20, 2)
        df['BB_Mid'] = df['Close'].rolling(20).mean()
        df['BB_Std'] = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
        
        # 4. MACD (12, 26, 9)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        return df

    def check_exit(self, position, current, prev):
        if position == 1:
            # Base Exit: RSI extreme overbought
            if current['RSI'] > self.rsi_sell:
                return f'RSI Over {self.rsi_sell} (Exit Long)', current['Close']
            
            # Auxiliary Exits
            if self.use_stoch and current['Stoch_K'] > 80 and current['Stoch_K'] < current['Stoch_D']:
                 return 'Stoch Bear Cross (Exit Long)', current['Close']
                 
            if self.use_macd and current['MACD'] < current['MACD_Signal'] and prev['MACD'] > prev['MACD_Signal']:
                 return 'MACD Bear Cross (Exit Long)', current['Close']
                 
        return None, None

    def check_entry(self, current, prev):
        if pd.isna(current['RSI']): 
            return 0
            
        # Base Requirement: RSI must be deeply oversold
        is_rsi_buy = current['RSI'] < self.rsi_buy
        
        # Auxiliary Requirements
        stoch_ok = True
        if self.use_stoch:
            # Stoch is oversold and K crosses above D (momentum shift)
            stoch_ok = current['Stoch_K'] < 20 and current['Stoch_K'] > current['Stoch_D'] and prev['Stoch_K'] <= prev['Stoch_D']
            
        bb_ok = True
        if self.use_bb:
            # Price pierced below the lower bollinger band (extreme panic)
            bb_ok = current['Low'] < current['BB_Lower']
            
        macd_ok = True
        if self.use_macd:
            # MACD line is ticking up (bullish convergence)
            macd_ok = current['MACD'] > current['MACD_Signal']
        
        if is_rsi_buy and stoch_ok and bb_ok and macd_ok:
            return 1
            
        return 0
