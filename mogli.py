import os
import time
import pandas as pd
from datetime import datetime, timedelta
from eqldata import generate_auth_token, get_1MARKET_DATA

# ---------------------------------------------------------
# 1. User Configuration
# ---------------------------------------------------------
USERNAME = 'kumarroshanjha786@gmail.com'
PASSWORD = '7CjFjKHy62m94xD3'

NIFTY_SYMBOL = "NSEIDX:NIFTY_50" 

# Define Start Date (Today's date will be automatically used as End Date)
START_DATE = "2026-09-01"          # Format: YYYY-MM-DD
END_DATE = datetime.today().strftime('%Y-%m-%d') 

# Brick Sizes
RENKO_BRICK_PCT_3M = 0.103
RENKO_BRICK_PCT_1M = 0.036

# --- PREVIOUS DAY RENKO ANCHORS (Just before START_DATE) ---
# Anchor for 3-minute Renko
PREV_LAST_BRICK_CLOSE_3M = 24072.00  
PREV_LAST_BRICK_DIR_3M = 'UP'       

# Anchor for 1-minute Renko
PREV_LAST_BRICK_CLOSE_1M = 24072.00
PREV_LAST_BRICK_DIR_1M = 'UP'       

NSE_HOLIDAYS_2026 = {
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26",
    "2026-03-31", "2026-04-03", "2026-04-14", "2026-05-01",
    "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02",
    "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25",
    "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10", 
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-08-15", 
    "2025-08-27", "2025-10-02", "2025-10-21", "2025-10-22", 
    "2025-11-05", "2025-12-25",
}

# ---------------------------------------------------------
# 2. Rate-Limit Wrapper Function
# ---------------------------------------------------------
def safe_fetch_market_data(token, instrument_list, target_date):
    max_retries = 5
    wait_time = 30  # Initial wait time in seconds

    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date)
            
            # Check for valid list-based response
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result

            # Check for API-level rate limit message
            result_str = str(result).lower()
            if "too many requests" in result_str or "429" in result_str:
                print(f" [!] Intraday Rate Limited. Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                wait_time += 10  # Increase wait time by 10s for the next try
                continue

            return result
            
        except Exception as e:
            # Check for Exception-level rate limit message
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str:
                print(f" [!] Intraday Rate Limited (Exception). Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                wait_time += 10  # Increase wait time by 10s for the next try
                continue
            else:
                print(f" [X] Unexpected Intraday API Error: {e}")
                return None
                
    print(f" [X] Max retries reached for {target_date}. Skipping.")
    return None

# ---------------------------------------------------------
# 3. Fetching, Resampling & Date Handling
# ---------------------------------------------------------
def get_trading_days(start_str, end_str, holidays):
    """Generate a list of valid trading dates avoiding weekends and holidays."""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    
    trading_days = []
    current = start
    while current <= end:
        # 5 = Saturday, 6 = Sunday
        if current.weekday() < 5:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in holidays:
                trading_days.append(date_str)
        current += timedelta(days=1)
    return trading_days

def fetch_data(token, symbol, date_str):
    print(f"[*] Fetching 1-min data for {symbol} on {date_str}...")
    
    # Use the safe fetch wrapper instead of direct API call
    raw_data = safe_fetch_market_data(token, [symbol], date_str)
    
    if not raw_data:
        return pd.DataFrame()

    flat_data = []
    def extract_ticks(lst):
        for item in lst:
            if isinstance(item, list):
                if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                    flat_data.append(item)
                else:
                    extract_ticks(item)
                    
    if isinstance(raw_data, list):
        extract_ticks(raw_data)
        
    if not flat_data:
        print(f"[-] No valid tick data found for {date_str}")
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
# 4. Renko Engine & Indicators
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
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Candle_Close': current_close, 'Direction': 'UP', 'Visual': '🟩 GREEN'})
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close <= (last_brick_close - (2 * rounded_pts)):
                    brick_open = last_brick_close - rounded_pts
                    brick_close = last_brick_close - (2 * rounded_pts)
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Candle_Close': current_close, 'Direction': 'DOWN', 'Visual': '🟥 RED'})
                    last_brick_close = brick_close
                    current_direction = 'DOWN'
                    brick_num += 1
                else: break

            elif current_direction == 'DOWN':
                if current_close <= (last_brick_close - rounded_pts):
                    brick_open = last_brick_close
                    brick_close = last_brick_close - rounded_pts
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Candle_Close': current_close, 'Direction': 'DOWN', 'Visual': '🟥 RED'})
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close >= (last_brick_close + (2 * rounded_pts)):
                    brick_open = last_brick_close + rounded_pts
                    brick_close = last_brick_close + (2 * rounded_pts)
                    renko_bricks.append({'Brick': brick_num, 'Timestamp': timestamp, 'Open': brick_open, 'Close': brick_close, 'Candle_Close': current_close, 'Direction': 'UP', 'Visual': '🟩 GREEN'})
                    last_brick_close = brick_close
                    current_direction = 'UP'
                    brick_num += 1
                else: break

    return pd.DataFrame(renko_bricks)

def add_indicators(df):
    if df.empty: return df
    
    # Calculate 9 EMA (Using the Brick Close for Indicator math as standard for Renko)
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
# 5. Strategy Backtesting Engine
# ---------------------------------------------------------
def run_backtest(renko_1m, renko_3m):
    trades = []
    position = 0 # 0 = Flat, 1 = Long, -1 = Short
    
    for idx_1m, row_1m in renko_1m.iterrows():
        current_time = row_1m['Timestamp']
        close_1m = row_1m['Close']            # Brick Close for indicators/conditions
        candle_close = row_1m['Candle_Close'] # Actual 1-min candle close for Execution price
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
            if trend_3m_is_positive and (rsi_3m < 70) and (close_1m > ema_1m):
                position = 1
                trades.append({
                    'Type': 'BUY', 
                    'Entry Time': current_time, 
                    'Entry Price (Candle)': candle_close,
                    'Entry EMA_1M': ema_1m,
                    'Entry EMA_3M': ema_3m,
                    'Entry RSI_3M': rsi_3m,
                    'Exit Time': None, 
                    'Exit Price (Candle)': None, 
                    'Exit EMA_1M': None,
                    'PnL': 0
                })
                
            elif trend_3m_is_negative and (rsi_3m > 30) and (close_1m < ema_1m):
                position = -1
                trades.append({
                    'Type': 'SELL', 
                    'Entry Time': current_time, 
                    'Entry Price (Candle)': candle_close,
                    'Entry EMA_1M': ema_1m,
                    'Entry EMA_3M': ema_3m,
                    'Entry RSI_3M': rsi_3m,
                    'Exit Time': None, 
                    'Exit Price (Candle)': None, 
                    'Exit EMA_1M': None,
                    'PnL': 0
                })

        elif position == 1:
            if close_1m < ema_1m:
                trades[-1]['Exit Time'] = current_time
                trades[-1]['Exit Price (Candle)'] = candle_close
                trades[-1]['Exit EMA_1M'] = ema_1m
                trades[-1]['PnL'] = candle_close - trades[-1]['Entry Price (Candle)']
                position = 0
                
        elif position == -1:
            if close_1m > ema_1m:
                trades[-1]['Exit Time'] = current_time
                trades[-1]['Exit Price (Candle)'] = candle_close
                trades[-1]['Exit EMA_1M'] = ema_1m
                trades[-1]['PnL'] = trades[-1]['Entry Price (Candle)'] - candle_close
                position = 0

    # Close open positions at the end of the dataset
    if position != 0:
        final_row = renko_1m.iloc[-1]
        final_price = final_row['Candle_Close']
        trades[-1]['Exit Time'] = final_row['Timestamp']
        trades[-1]['Exit Price (Candle)'] = final_price
        trades[-1]['Exit EMA_1M'] = final_row['EMA_9']
        trades[-1]['PnL'] = (final_price - trades[-1]['Entry Price (Candle)']) if position == 1 else (trades[-1]['Entry Price (Candle)'] - final_price)

    return pd.DataFrame(trades)


# ---------------------------------------------------------
# 6. Main Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    auth_token = generate_auth_token(USERNAME, PASSWORD)
    if not auth_token:
        print("[X] Auth Failed.")
        exit(1)

    # 1. Determine valid trading dates
    trading_dates = get_trading_days(START_DATE, END_DATE, NSE_HOLIDAYS_2026)
    print(f"[*] Planning to fetch data for {len(trading_dates)} trading days between {START_DATE} and {END_DATE}...")

    # 2. Fetch and aggregate all day data
    all_1m_data = []
    for d in trading_dates:
        daily_df = fetch_data(auth_token, NIFTY_SYMBOL, d)
        if not daily_df.empty:
            all_1m_data.append(daily_df)
    
    if not all_1m_data:
        print("[!] No data available for the given date range.")
        exit()
        
    # Combine into a single continuous DataFrame across the date range
    df_1m_raw = pd.concat(all_1m_data).sort_index()
    
    df_1m = df_1m_raw.reset_index()
    df_3m = resample_data(df_1m_raw, "3min")

    print(f"\n[*] Generating Continuous 3-Min Renko Chart ({RENKO_BRICK_PCT_3M}%)...")
    renko_3m = create_percentage_renko(df_3m, RENKO_BRICK_PCT_3M, PREV_LAST_BRICK_CLOSE_3M, PREV_LAST_BRICK_DIR_3M)
    renko_3m = add_indicators(renko_3m)

    print(f"[*] Generating Continuous 1-Min Renko Chart ({RENKO_BRICK_PCT_1M}%)...")
    renko_1m = create_percentage_renko(df_1m, RENKO_BRICK_PCT_1M, PREV_LAST_BRICK_CLOSE_1M, PREV_LAST_BRICK_DIR_1M)
    renko_1m = add_indicators(renko_1m)

    # Format Pandas to output all rows for the console request
    pd.set_option('display.max_rows', None)

    # Print Samples (ALL BRICKS)
    print("\n--- 3 MINUTE RENKO (ALL BRICKS) ---")
    print(renko_3m[['Brick', 'Timestamp', 'Close', 'Candle_Close', 'EMA_9', 'RSI_14', 'Direction', 'Visual']].to_string(index=False))

    print("\n--- 1 MINUTE RENKO (ALL BRICKS) ---")
    print(renko_1m[['Brick', 'Timestamp', 'Close', 'Candle_Close', 'EMA_9', 'RSI_14', 'Direction', 'Visual']].to_string(index=False))

    # Run Backtest
    print("\n[*] Running Trading Strategy Backtest...")
    trades_df = run_backtest(renko_1m, renko_3m)
    
    # Save everything to a multi-sheet Excel file
    filename = f"Renko_Data_and_Trades_{START_DATE}_to_{END_DATE}.xlsx"
    
    # Convert timestamps to naive for Excel compatibility (removes timezone warnings)
    for df in [trades_df, renko_1m, renko_3m]:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        trades_df.to_excel(writer, sheet_name='Trade_Log', index=False)
        renko_3m.to_excel(writer, sheet_name='Renko_3M_Data', index=False)
        renko_1m.to_excel(writer, sheet_name='Renko_1M_Data', index=False)
        
    print(f"\n[+] Full dataset (Trades, 1M Bricks, 3M Bricks) successfully exported to: {filename}")