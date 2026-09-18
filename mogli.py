import os
import time
import pandas as pd
from datetime import datetime
from eqldata import generate_auth_token, get_1MARKET_DATA

# ---------------------------------------------------------
# 1. User Configuration
# ---------------------------------------------------------
USERNAME = 'kumarroshanjha786@gmail.com'
PASSWORD = '7CjFjKHy62m94xD3'

NIFTY_SYMBOL = "NSEIDX:NIFTY_50" 
TARGET_DATE = "2026-09-17"          # Format: YYYY-MM-DD

# Brick Sizes
RENKO_BRICK_PCT_3M = 0.103
RENKO_BRICK_PCT_1M = 0.036

# --- PREVIOUS DAY RENKO ANCHORS ---
# Anchor for 3-minute Renko
PREV_LAST_BRICK_CLOSE_3M = 23221.92  
PREV_LAST_BRICK_DIR_3M = 'DOWN'       

# Anchor for 1-minute Renko
PREV_LAST_BRICK_CLOSE_1M = 23223.87
PREV_LAST_BRICK_DIR_1M = 'DOWN'       


# ---------------------------------------------------------
# 2. Fetching & Resampling Data
# ---------------------------------------------------------
def fetch_data(token, symbol, date_str):
    print(f"[*] Fetching 1-min data for {symbol} on {date_str}...")
    try:
        raw_data = get_1MARKET_DATA(token, [symbol], date_str)
    except Exception as e:
        print(f"[X] API Error: {e}")
        return pd.DataFrame()

    flat_data = []
    def extract_ticks(lst):
        for item in lst:
            if isinstance(item, list):
                if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                    flat_data.append(item)
                else:
                    extract_ticks(item)
                    
    if raw_data and isinstance(raw_data, list):
        extract_ticks(raw_data)
        
    if not flat_data:
        return pd.DataFrame()

    columns = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
    df = pd.DataFrame(flat_data, columns=columns)
    df['Timestamp'] = df['Timestamp'].str.replace(' ', '')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d%H:%M:%S')
    
    cols_to_numeric = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric)
    return df.sort_values('Timestamp').set_index('Timestamp')

def resample_data(df, timeframe):
    resampled_df = df.resample(timeframe).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna().reset_index()
    return resampled_df


# ---------------------------------------------------------
# 3. Renko Engine & Indicators
# ---------------------------------------------------------
def create_percentage_renko(df, brick_pct, anchor_close, anchor_dir):
    if df.empty: return pd.DataFrame()
    renko_bricks = []
    
    last_brick_close = anchor_close
    current_direction = anchor_dir
    brick_num = 1

    for _, row in df.iterrows():
        current_close = row['Close']
        timestamp = row['Timestamp']

        while True:
            raw_pts = last_brick_close * (brick_pct / 100.0)
            rounded_pts = max(1, round(raw_pts))

            if current_direction == 'UP':
                if current_close >= (last_brick_close + rounded_pts):
                    brick_open = last_brick_close
                    brick_close = last_brick_close + rounded_pts
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Direction': 'UP', 'Visual': '🟩 GREEN'})
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close <= (last_brick_close - (2 * rounded_pts)):
                    brick_open = last_brick_close - rounded_pts
                    brick_close = last_brick_close - (2 * rounded_pts)
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Direction': 'DOWN', 'Visual': '🟥 RED'})
                    last_brick_close = brick_close
                    current_direction = 'DOWN'
                    brick_num += 1
                else: break

            elif current_direction == 'DOWN':
                if current_close <= (last_brick_close - rounded_pts):
                    brick_open = last_brick_close
                    brick_close = last_brick_close - rounded_pts
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Direction': 'DOWN', 'Visual': '🟥 RED'})
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close >= (last_brick_close + (2 * rounded_pts)):
                    brick_open = last_brick_close + rounded_pts
                    brick_close = last_brick_close + (2 * rounded_pts)
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Direction': 'UP', 'Visual': '🟩 GREEN'})
                    last_brick_close = brick_close
                    current_direction = 'UP'
                    brick_num += 1
                else: break

    return pd.DataFrame(renko_bricks)

def add_indicators(df):
    if df.empty: return df
    
    # Calculate 9 EMA
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    
    # Calculate RSI (14) - Wilder's Smoothing
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # Fill NaN for early bricks
    df['RSI_14'] = df['RSI_14'].fillna(50) 
    return df


# ---------------------------------------------------------
# 4. Strategy Backtesting Engine
# ---------------------------------------------------------
def run_backtest(renko_1m, renko_3m):
    trades = []
    position = 0 # 0 = Flat, 1 = Long, -1 = Short
    entry_price = 0.0
    entry_time = None
    
    for idx_1m, row_1m in renko_1m.iterrows():
        current_time = row_1m['Timestamp']
        close_1m = row_1m['Close']
        ema_1m = row_1m['EMA_9']
        
        # Get the latest 3M state that occurred AT OR BEFORE this 1M brick
        past_3m_bricks = renko_3m[renko_3m['Timestamp'] <= current_time]
        if past_3m_bricks.empty:
            continue
            
        latest_3m = past_3m_bricks.iloc[-1]
        close_3m = latest_3m['Close']
        ema_3m = latest_3m['EMA_9']
        rsi_3m = latest_3m['RSI_14']
        
        # Determine 3-min Trend Conditions
        trend_3m_is_positive = (close_3m > ema_3m)
        trend_3m_is_negative = (close_3m < ema_3m)
        
        # Strategy Logic
        if position == 0:
            # Entry Logic
            if trend_3m_is_positive and (rsi_3m < 70) and (close_1m > ema_1m):
                position = 1
                entry_price = close_1m
                entry_time = current_time
                trades.append({'Type': 'BUY (Long)', 'Entry Time': entry_time, 'Entry Price': entry_price, 'Exit Time': None, 'Exit Price': None, 'PnL': 0})
                
            elif trend_3m_is_negative and (rsi_3m > 30) and (close_1m < ema_1m):
                position = -1
                entry_price = close_1m
                entry_time = current_time
                trades.append({'Type': 'SELL (Short)', 'Entry Time': entry_time, 'Entry Price': entry_price, 'Exit Time': None, 'Exit Price': None, 'PnL': 0})

        elif position == 1:
            # Exit Long Logic (if 1m close drops below 1m EMA)
            if close_1m < ema_1m:
                trades[-1]['Exit Time'] = current_time
                trades[-1]['Exit Price'] = close_1m
                trades[-1]['PnL'] = close_1m - trades[-1]['Entry Price']
                position = 0
                
        elif position == -1:
            # Exit Short Logic (if 1m close rises above 1m EMA)
            if close_1m > ema_1m:
                trades[-1]['Exit Time'] = current_time
                trades[-1]['Exit Price'] = close_1m
                trades[-1]['PnL'] = trades[-1]['Entry Price'] - close_1m
                position = 0

    # Close open positions at the end of the day
    if position != 0:
        final_price = renko_1m.iloc[-1]['Close']
        trades[-1]['Exit Time'] = renko_1m.iloc[-1]['Timestamp']
        trades[-1]['Exit Price'] = final_price
        trades[-1]['PnL'] = (final_price - trades[-1]['Entry Price']) if position == 1 else (trades[-1]['Entry Price'] - final_price)

    return pd.DataFrame(trades)


# ---------------------------------------------------------
# 5. Main Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    auth_token = generate_auth_token(USERNAME, PASSWORD)
    if not auth_token:
        print("[X] Auth Failed.")
        exit(1)

    # Fetch and prepare DataFrames
    df_1m_raw = fetch_data(auth_token, NIFTY_SYMBOL, TARGET_DATE)
    
    if df_1m_raw.empty:
        print("[!] No data available.")
        exit()
        
    df_1m = df_1m_raw.reset_index()
    df_3m = resample_data(df_1m_raw, "3min")

    print(f"\n[*] Generating 3-Min Renko Chart ({RENKO_BRICK_PCT_3M}%)...")
    renko_3m = create_percentage_renko(df_3m, RENKO_BRICK_PCT_3M, PREV_LAST_BRICK_CLOSE_3M, PREV_LAST_BRICK_DIR_3M)
    renko_3m = add_indicators(renko_3m)

    print(f"[*] Generating 1-Min Renko Chart ({RENKO_BRICK_PCT_1M}%)...")
    renko_1m = create_percentage_renko(df_1m, RENKO_BRICK_PCT_1M, PREV_LAST_BRICK_CLOSE_1M, PREV_LAST_BRICK_DIR_1M)
    renko_1m = add_indicators(renko_1m)

    # Print Samples
    print("\n--- 3 MINUTE RENKO (LAST 5 BRICKS) ---")
    print(renko_3m[['Timestamp', 'Close', 'EMA_9', 'RSI_14', 'Direction']].tail())

    print("\n--- 1 MINUTE RENKO (LAST 5 BRICKS) ---")
    print(renko_1m[['Timestamp', 'Close', 'EMA_9', 'RSI_14', 'Direction']].tail())

    # Run Backtest
    print("\n[*] Running Trading Strategy Backtest...")
    trades_df = run_backtest(renko_1m, renko_3m)

    if not trades_df.empty:
        total_pnl = trades_df['PnL'].sum()
        print("\n" + "="*85)
        print(f"{'TRADE LOG':^85}")
        print("="*85)
        print(trades_df.to_string(index=False))
        print("="*85)
        print(f"Total Trades Taken: {len(trades_df)}")
        print(f"Net Points (PnL)  : {total_pnl:.2f} points")
        
        # Save to Excel
        filename = f"renko_trades_{TARGET_DATE}.xlsx"
        trades_df.to_excel(filename, index=False)
        print(f"\n[+] Trade results successfully exported to: {filename}")
    else:
        print("\n[!] No trades were triggered based on the strategy conditions.")