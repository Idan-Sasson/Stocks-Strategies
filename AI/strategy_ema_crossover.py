import pandas as pd

class EMACrossoverStrategy:
    """
    Standard EMA Crossover Strategy: 9 EMA vs 21 EMA.
    Reverses immediately upon cross back.
    """
    def __init__(self):
        pass
        
    def calculate_indicators(self, df):
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        return df

    def check_exit(self, position, current, prev):
        # We need to manually check for signal reversal here to exit the trade 
        # BEFORE the stop loss or take profit hits
        if position == 1 and current['EMA_9'] < current['EMA_21']:
            return 'Signal Reversal', current['Close']
        elif position == -1 and current['EMA_9'] > current['EMA_21']:
            return 'Signal Reversal', current['Close']
            
        return None, None # Rely on Engine SL / TP / EOD

    def check_entry(self, current, prev):
        if pd.isna(current['EMA_21']): 
            return 0
            
        crossover_up = prev['EMA_9'] <= prev['EMA_21'] and current['EMA_9'] > current['EMA_21']
        crossover_down = prev['EMA_9'] >= prev['EMA_21'] and current['EMA_9'] < current['EMA_21']
        
        if crossover_up:
            return 1
        elif crossover_down:
            return -1
            
        return 0
