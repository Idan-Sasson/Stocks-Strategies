import subprocess
import os

scripts = [
    "strategy_ema_crossover.py",
    "strategy_rsi_reversion.py",
    "strategy_macd_trend.py",
    "strategy_bollinger.py",
    "strategy_orb.py"
]

print("=== RUNNING 5 DAYTRADING STRATEGIES ===")
for script in scripts:
    print(f"Running {script}...")
    try:
        # Check if file exists to prevent errors
        if os.path.exists(script):
            result = subprocess.run(["python", script], capture_output=True, text=True)
            output = result.stdout.strip().split('\n')
            if len(output) > 0:
                print(output[-1]) # Show just the last line containing the print summary!
            else:
                print("No output.")
        else:
            print(f"Error: {script} not found.")
    except Exception as e:
        print(f"Failed to run {script}: {e}")
    print("-" * 40)
print("=== FINISHED ===")
