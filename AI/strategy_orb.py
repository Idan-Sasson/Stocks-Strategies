import pandas as pd
from datetime import time

class ORBStrategy:
    """
    15-minute Opening Range Breakout Strategy.
    """
    def __init__(self):
        self.traded_today = False
        
    def calculate_indicators(self, df):
        # ORB 15 mins (09:30 to 09:44)
        # The bars up to 09:40 include data until 09:45
        or_cond = df['Time'] <= time(9, 40) 
        
        daily_or_high = df[or_cond].groupby('Date')['High'].max()
        daily_or_low = df[or_cond].groupby('Date')['Low'].min()
        
        df = df.join(daily_or_high.rename('OR_High'), on='Date')
        df = df.join(daily_or_low.rename('OR_Low'), on='Date')
        return df

    def reset_state(self):
        self.traded_today = False
        
    def on_new_day(self, date):
        self.traded_today = False
        
    def on_trade_exit(self):
        pass

    def check_exit(self, position, current, prev):
        # Rely completely on Engine for SL / TP / EOD exits
        return None, None 

    def check_entry(self, current, prev):
        if self.traded_today:
            return 0
            
        is_post_or = (current['Time'] >= time(9, 45))     
        is_too_late = (current['Time'] >= time(12, 0))    
        
        if not is_post_or or is_too_late:
            return 0
            
        if pd.isna(current['OR_High']): 
            return 0
            
        breakout_up = current['Close'] > current['OR_High']
        breakout_down = current['Close'] < current['OR_Low']
        
        if breakout_up: 
            self.traded_today = True
            return 1
        elif breakout_down: 
            self.traded_today = True
            return -1
            
        return 0
