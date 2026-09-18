import os
import time
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_1MARKET_DATA
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Configuration & Timeframe Settings
# ---------------------------------------------------------

username = 'kumarroshanjha004@outlook.com'
password = 'Roshan@123'

# --- DYNAMIC INDICATOR SETTINGS ---
# Use standard Pandas offset strings: '1min', '5min', '10min', '30min', '60min', '1D'
TIMEFRAME = '1min'       
SMA_PERIOD = 20            
MAX_LOOKBACK_DAYS = 40      # Safety failsafe to prevent infinite loops on dead stocks

auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")

# ---------------------------------------------------------
# 2. Smart Trading Calendar (2026)
# ---------------------------------------------------------
NSE_HOLIDAYS_2026 = {
    "2026-01-15", # Municipal Corporation Election
    "2026-01-26", # Republic Day
    "2026-03-03", # Holi
    "2026-03-26", # Shri Ram Navami
    "2026-03-31", # Shri Mahavir Jayanti
    "2026-04-03", # Good Friday
    "2026-04-14", # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01", # Maharashtra Day
    "2026-05-28", # Bakri Id
    "2026-06-26", # Muharram
    "2026-09-14", # Ganesh Chaturthi
    "2026-10-02", # Mahatma Gandhi Jayanti
    "2026-10-20", # Dussehra
    "2026-11-10", # Diwali-Balipratipada
    "2026-11-24", # Prakash Gurpurb Sri Guru Nanak Dev
    "2026-12-25"  # Christmas
}


def get_previous_trading_day(current_date):
    """Walks backward 1 day at a time until it finds a valid trading day."""
    current_date -= timedelta(days=1)
    while current_date.weekday() >= 5 or current_date.strftime("%Y-%m-%d") in NSE_HOLIDAYS_2026:
        current_date -= timedelta(days=1)
    return current_date

# ---------------------------------------------------------
# 3. API Wrapper & Extractor
# ---------------------------------------------------------
def safe_fetch_market_data(token, instrument_list, target_date_str):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date_str)
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result
            if "too many requests" in str(result).lower() or "429" in str(result).lower():
                print(f" [!] Rate Limited. Waiting 30s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(30)
                continue
            return result
        except Exception as e:
            print(f" [X] Error: {e}")
            return None
    return None

def extract_flattened_data(nested_list, master_list):
    """Recursively pulls rows from the messy API payload into a single flat list."""
    for item in nested_list:
        if isinstance(item, list):
            if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                master_list.append(item)
            else:
                extract_flattened_data(item, master_list)

# ---------------------------------------------------------
# 4. Main Execution & Iterative Lookback Loop
# ---------------------------------------------------------
instruments = [
    "NSEEQ:RELIANCE",
]

if auth_token:
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_fetch_date = datetime.strptime(today_str, "%Y-%m-%d")
    
    all_combined_data = []
    days_fetched = 0
    df_resampled_final = None

    print(f"Targeting Timeframe: {TIMEFRAME} | Required Candles: {SMA_PERIOD}")
    print("-" * 50)

    # LOOP: Fetch -> Check if enough candles -> If not, go back 1 day and fetch again
    while days_fetched < MAX_LOOKBACK_DAYS:
        date_str = current_fetch_date.strftime("%Y-%m-%d")
        print(f"Fetching data for: {date_str}...")
        
        raw_data = safe_fetch_market_data(auth_token, instruments, date_str)
        if raw_data and isinstance(raw_data, list):
            extract_flattened_data(raw_data, all_combined_data)
            
        # 1. Convert everything fetched so far into a DataFrame
        if not all_combined_data:
            print("No data received yet, checking previous day...")
        else:
            cols = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
            df = pd.DataFrame(all_combined_data, columns=cols)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace(' ', ''), format='%Y-%m-%d%H:%M:%S')
            df[cols[2:7]] = df[cols[2:7]].apply(pd.to_numeric)
            
            # 2. Resample Data to the target timeframe
            df.set_index('Timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            resampled_frames = []
            candles_sufficient = True
            
            # Check every requested symbol
            for symbol in instruments:
                clean_symbol = symbol.split(":")[1] # Extract 'RELIANCE' from 'NSEEQ:RELIANCE'
                symbol_df = df[df['Symbol'] == clean_symbol]
                
                # Resample logic
                resampled = symbol_df.resample(TIMEFRAME).agg({
                    'Symbol': 'first',
                    'Open': 'first', 
                    'High': 'max', 
                    'Low': 'min', 
                    'Close': 'last', 
                    'Volume': 'sum'
                }).dropna()
                
                resampled_frames.append(resampled)
                
                # Check if this specific stock hit the 20 candle requirement
                if len(resampled) < SMA_PERIOD:
                    candles_sufficient = False

            # 3. Decision Gate
            if candles_sufficient:
                print(f"-> Success! Successfully built >= {SMA_PERIOD} candles for all instruments.")
                df_resampled_final = pd.concat(resampled_frames)
                break
            else:
                print(f"   -> Not enough {TIMEFRAME} candles yet. Walking back another day...")

        # Move logic to previous valid trading day
        current_fetch_date = get_previous_trading_day(current_fetch_date)
        days_fetched += 1

    # ---------------------------------------------------------
    # 5. Calculate and Display Final SMA
    # ---------------------------------------------------------
    if df_resampled_final is not None:
        print("\n" + "=" * 70)
        print(f"{'SYMBOL':<15} | {'TIMEFRAME':<10} | {'LATEST CLOSE':<15} | {f'SMA-{SMA_PERIOD}':<10}")
        print("=" * 70)
        
        for symbol, group in df_resampled_final.groupby('Symbol'):
            group = group.sort_index()
            group['SMA'] = group['Close'].rolling(window=SMA_PERIOD).mean()
            
            latest_candle = group.iloc[-1]
            print(f"{symbol:<15} | {TIMEFRAME:<10} | {latest_candle['Close']:<15.2f} | {latest_candle['SMA']:<10.2f}")
            
        print("=" * 70)
    else:
        print(f"\n[!] Reached max lookback limit ({MAX_LOOKBACK_DAYS} days) without satisfying candle requirement.")