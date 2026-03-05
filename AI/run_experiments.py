from engine import SimulationEngine
from strategy_swing_rsi import SwingRSIStrategy

# --- CONFIGURATION (Central Hub) ---
config = {
    "ticker": "QQQ",
    "period": "3y",
    "interval": "1d",          # Daily for swings
    "initial_capital": 10000.0,
    "trade_fee": 3.0,          
    "trade_size_pct": 1.0,       
    "use_sl_tp": False,        # RSI handles exits
    "exit_at_eod": False       # Hold overnight
}

print("=== STARTING SWING TRADING SIMULATION ===")

# 1. Initialize Engine
engine = SimulationEngine(
    ticker=config["ticker"],
    period=config["period"],
    interval=config["interval"],
    initial_capital=config["initial_capital"],
    trade_fee=config["trade_fee"],
    trade_size_pct=config["trade_size_pct"],
    use_sl_tp=config["use_sl_tp"],
    exit_at_eod=config["exit_at_eod"]
)

# 2. Load Strategy
strategy = SwingRSIStrategy(rsi_buy=30, rsi_sell=70)

# 3. Run Simulation
trades_df, final_capital = engine.run(strategy)

# 4. Show Results
engine.print_results(trades_df, final_capital, "Swing RSI (30/70)")

if not trades_df.empty:
    print("\nIndividual Trades:")
    print(trades_df[['Exit_Time', 'Type', 'Reason', 'Net_PnL', 'Capital']].tail(10))
else:
    print("Check indicators or logic - 0 trades executed.")
