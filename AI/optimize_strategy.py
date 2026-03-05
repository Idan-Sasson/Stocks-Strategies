import pandas as pd
from engine import SimulationEngine
from strategy_swing_composite import SwingCompositeStrategy

def optimize():
    ticker = 'SPY'
    period = '3y'
    interval = '1d'
    
    # 1. RSI Grid
    buy_levels = [30, 35]
    sell_levels = [70, 75, 80]
    
    # 2. Indicator Toggles Grid
    use_stoch_options = [False, True]
    use_bb_options = [False, True]
    
    results = []
    
    print(f"Starting Multi-Indicator Optimization for {ticker} over {period}...")
    
    # Initialize Engine once (and fetch data once for speed)
    engine = SimulationEngine(
        ticker=ticker, 
        period=period, 
        interval=interval,
        use_sl_tp=False,   # Strategy handles exits
        exit_at_eod=False  # Swing trading
    )
    engine.fetch_data() # Pre-fetch
    
    total_runs = len(buy_levels) * len(sell_levels) * len(use_stoch_options) * len(use_bb_options)
    current_run = 0
    
    for buy in buy_levels:
        for sell in sell_levels:
            for use_stoch in use_stoch_options:
                for use_bb in use_bb_options:
                    current_run += 1
                    print(f"Running {current_run}/{total_runs} (Buy:{buy}, Sell:{sell}, Stoch:{use_stoch}, BB:{use_bb})...", end="\r")
                    
                    strategy = SwingCompositeStrategy(
                        rsi_buy=buy, 
                        rsi_sell=sell,
                        use_stoch=use_stoch,
                        use_bb=use_bb,
                        use_macd=False # Keeping MACD off for this search to limit grid size
                    )
                    
                    trades_df, final_cap = engine.run(strategy)
                    
                    net_pnl = final_cap - engine.initial_capital
                    win_rate = 0
                    avg_days = 0
                    
                    if not trades_df.empty:
                        wins = len(trades_df[trades_df['Net_PnL'] > 0])
                        win_rate = (wins / len(trades_df)) * 100
                        avg_days = trades_df['Days_Held'].mean()
                    
                    if len(trades_df) > 0: # Only save if it actually traded
                        results.append({
                            'RSI_Buy': buy,
                            'RSI_Sell': sell,
                            'Stoch': 'Yes' if use_stoch else 'No',
                            'Bollinger': 'Yes' if use_bb else 'No',
                            'Net_PnL': net_pnl,
                            'Trades': len(trades_df),
                            'WinRate': win_rate,
                            'AvgDays': round(avg_days, 1)
                        })

    print("\n\n" + "="*80)
    print("TOP 5 OPTIMIZATION RESULTS:")
    print("="*80)
    
    if len(results) > 0:
        optim_df = pd.DataFrame(results).sort_values(by='Net_PnL', ascending=False)
        print(optim_df.head(5).to_string(index=False))
    else:
        print("No profitable combinations found.")
        
    print("="*80)

if __name__ == "__main__":
    optimize()
