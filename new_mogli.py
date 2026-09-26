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
START_DATE = "2026-09-01"          
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
    wait_time = 30  

    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date)
            
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result

            result_str = str(result).lower()
            if "too many requests" in result_str or "429" in result_str:
                print(f" [!] Intraday Rate Limited. Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                wait_time += 10  
                continue

            return result
            
        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str:
                print(f" [!] Intraday Rate Limited (Exception). Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
                wait_time += 10  
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
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    
    trading_days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in holidays:
                trading_days.append(date_str)
        current += timedelta(days=1)
    return trading_days



def fetch_data(token, symbol, date_str):
    print(f"[*] Fetching 1-min data for {symbol} on {date_str}...")
    
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
# 4. Renko Engine
# ---------------------------------------------------------
def create_percentage_renko(df, brick_pct, anchor_close, anchor_dir):
    if df.empty: return pd.DataFrame()
    renko_bricks = []
    
    last_brick_close = anchor_close
    current_direction = anchor_dir
    brick_num = 1

    for _, row in df.iterrows():
        current_open = row['Open']
        current_close = row['Close']
        timestamp = row['Timestamp']

        while True:
            # Calculate dynamic brick size for the current price level
            raw_pts = last_brick_close * (brick_pct / 100.0)
            rounded_pts = max(1, round(raw_pts))

            if current_direction == 'UP':
                if current_close >= (last_brick_close + rounded_pts):
                    brick_open = last_brick_close
                    brick_close = last_brick_close + rounded_pts
                    renko_bricks.append({
                        'Brick': brick_num, 
                        'Timestamp': timestamp, 
                        'Brick_Opening_Price': brick_open,
                        'Brick_Closing_Price': brick_close, 
                        'Candle_Open': current_open,
                        'Candle_Closing': current_close, 
                        'Direction': 'UP', 
                        'Brick_Size': rounded_pts, 
                        'Visual': '🟩 GREEN'
                    })
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close <= (last_brick_close - (2 * rounded_pts)):
                    brick_open = last_brick_close - rounded_pts
                    brick_close = last_brick_close - (2 * rounded_pts)
                    renko_bricks.append({
                        'Brick': brick_num, 
                        'Timestamp': timestamp, 
                        'Brick_Opening_Price': brick_open,
                        'Brick_Closing_Price': brick_close, 
                        'Candle_Open': current_open,
                        'Candle_Closing': current_close, 
                        'Direction': 'DOWN', 
                        'Brick_Size': rounded_pts, 
                        'Visual': '🟥 RED'
                    })
                    last_brick_close = brick_close
                    current_direction = 'DOWN'
                    brick_num += 1
                else: break

            elif current_direction == 'DOWN':
                if current_close <= (last_brick_close - rounded_pts):
                    brick_open = last_brick_close
                    brick_close = last_brick_close - rounded_pts
                    renko_bricks.append({
                        'Brick': brick_num, 
                        'Timestamp': timestamp, 
                        'Brick_Opening_Price': brick_open,
                        'Brick_Closing_Price': brick_close, 
                        'Candle_Open': current_open,
                        'Candle_Closing': current_close, 
                        'Direction': 'DOWN', 
                        'Brick_Size': rounded_pts, 
                        'Visual': '🟥 RED'
                    })
                    last_brick_close = brick_close
                    brick_num += 1
                elif current_close >= (last_brick_close + (2 * rounded_pts)):
                    brick_open = last_brick_close + rounded_pts
                    brick_close = last_brick_close + (2 * rounded_pts)
                    renko_bricks.append({
                        'Brick': brick_num, 
                        'Timestamp': timestamp, 
                        'Brick_Opening_Price': brick_open,
                        'Brick_Closing_Price': brick_close, 
                        'Candle_Open': current_open,
                        'Candle_Closing': current_close, 
                        'Direction': 'UP', 
                        'Brick_Size': rounded_pts, 
                        'Visual': '🟩 GREEN'
                    })
                    last_brick_close = brick_close
                    current_direction = 'UP'
                    brick_num += 1
                else: break

    return pd.DataFrame(renko_bricks)



# ---------------------------------------------------------
# 5. Main Execution
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

    print(f"[*] Generating Continuous 1-Min Renko Chart ({RENKO_BRICK_PCT_1M}%)...")
    renko_1m = create_percentage_renko(df_1m, RENKO_BRICK_PCT_1M, PREV_LAST_BRICK_CLOSE_1M, PREV_LAST_BRICK_DIR_1M)

    # Format Pandas to output all rows for the console request
    pd.set_option('display.max_rows', None)

    # Print Samples (ALL BRICKS)
    print("\n--- 3 MINUTE RENKO (ALL BRICKS) ---")
    print(renko_3m[['Brick', 'Timestamp', 'Brick_Opening_Price', 'Brick_Closing_Price', 'Candle_Open', 'Candle_Closing', 'Direction', 'Brick_Size', 'Visual']].head(20).to_string(index=False))
    print("... (Truncated for terminal view)")

    print("\n--- 1 MINUTE RENKO (ALL BRICKS) ---")
    print(renko_1m[['Brick', 'Timestamp', 'Brick_Opening_Price', 'Brick_Closing_Price', 'Candle_Open', 'Candle_Closing', 'Direction', 'Brick_Size', 'Visual']].head(20).to_string(index=False))
    print("... (Truncated for terminal view)")

    # Save to Excel
    filename = f"Renko_Bricks_{START_DATE}_to_{END_DATE}.xlsx"
    
    # Convert timestamps to naive for Excel compatibility (removes timezone warnings)
    for df in [renko_1m, renko_3m]:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        renko_3m.to_excel(writer, sheet_name='Renko_3M_Bricks', index=False)
        renko_1m.to_excel(writer, sheet_name='Renko_1M_Bricks', index=False)
        
    print(f"\n[+] Renko charts successfully exported to: {filename}")