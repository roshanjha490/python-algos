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
TIMEFRAME = '5min'       
SMA_PERIOD = 20            
MAX_LOOKBACK_DAYS = 40     

auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")

NSE_HOLIDAYS_2026 = {
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26",
    "2026-03-31", "2026-04-03", "2026-04-14", "2026-05-01",
    "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02",
    "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"
}

def get_previous_trading_day(current_date):
    current_date -= timedelta(days=1)
    while current_date.weekday() >= 5 or current_date.strftime("%Y-%m-%d") in NSE_HOLIDAYS_2026:
        current_date -= timedelta(days=1)
    return current_date

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
    for item in nested_list:
        if isinstance(item, list):
            if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                master_list.append(item)
            else:
                extract_flattened_data(item, master_list)

# ---------------------------------------------------------
# NEW: Data Processing Helper
# ---------------------------------------------------------
def process_into_dataframe(raw_list):
    """Converts the raw API list into a clean Pandas DataFrame."""
    if not raw_list:
        return pd.DataFrame()
    cols = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
    df = pd.DataFrame(raw_list, columns=cols)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace(' ', ''), format='%Y-%m-%d%H:%M:%S')
    df[cols[2:7]] = df[cols[2:7]].apply(pd.to_numeric)
    return df

def calculate_and_print_sma(df, timeframe, sma_period, instruments):
    """Resamples the DataFrame and prints the current SMA state."""
    print("\n" + "=" * 70)
    print(f"{'SYMBOL':<15} | {'TIMEFRAME':<10} | {'LATEST CLOSE':<15} | {f'SMA-{sma_period}':<10}")
    print("=" * 70)
    
    for symbol in instruments:
        clean_symbol = symbol.split(":")[1]
        symbol_df = df[df['Symbol'] == clean_symbol].copy()
        
        if symbol_df.empty:
            continue
            
        symbol_df.set_index('Timestamp', inplace=True)
        symbol_df.sort_index(inplace=True)
        
        resampled = symbol_df.resample(timeframe).agg({
            'Symbol': 'first', 'Open': 'first', 'High': 'max', 
            'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(resampled) >= sma_period:
            resampled['SMA'] = resampled['Close'].rolling(window=sma_period).mean()
            latest = resampled.iloc[-1]
            print(f"{clean_symbol:<15} | {timeframe:<10} | {latest['Close']:<15.2f} | {latest['SMA']:<10.2f}")
        else:
            print(f"{clean_symbol:<15} | {timeframe:<10} | Needs more data ({len(resampled)}/{sma_period})")
            
    print("=" * 70)

# ---------------------------------------------------------
# 4. Main Execution
# ---------------------------------------------------------
instruments = ["NSEEQ:RELIANCE", "NSEEQ:TCS", "NSEEQ:HDFCBANK"]

if auth_token:
    today_str = "2026-06-09" # In production, use: datetime.now().strftime("%Y-%m-%d")
    current_fetch_date = datetime.strptime(today_str, "%Y-%m-%d")
    
    # --- PHASE 1: BOOTSTRAP (Fetch History) ---
    print(f"--- STARTING BOOTSTRAP PHASE ---")
    all_combined_data = []
    days_fetched = 0
    master_df = pd.DataFrame()

    while days_fetched < MAX_LOOKBACK_DAYS:
        date_str = current_fetch_date.strftime("%Y-%m-%d")
        print(f"Bootstrapping historical data for: {date_str}...")
        
        raw_data = safe_fetch_market_data(auth_token, instruments, date_str)
        if raw_data and isinstance(raw_data, list):
            extract_flattened_data(raw_data, all_combined_data)
            
        if all_combined_data:
            temp_df = process_into_dataframe(all_combined_data)
            
            # Check if we have enough data
            candles_sufficient = True
            for symbol in instruments:
                clean_symbol = symbol.split(":")[1]
                sym_df = temp_df[temp_df['Symbol'] == clean_symbol]
                
                if not sym_df.empty:
                    sym_df = sym_df.set_index('Timestamp').sort_index()
                    resampled = sym_df.resample(TIMEFRAME).agg({'Close': 'last'}).dropna()
                    if len(resampled) < SMA_PERIOD:
                        candles_sufficient = False
                else:
                    candles_sufficient = False

            if candles_sufficient:
                master_df = temp_df
                print(f"-> Bootstrap Success! Acquired enough historical data.")
                break

        current_fetch_date = get_previous_trading_day(current_fetch_date)
        days_fetched += 1

    # Perform initial calculation
    calculate_and_print_sma(master_df, TIMEFRAME, SMA_PERIOD, instruments)

    # --- PHASE 2: LIVE POLLING LOOP ---
    print("\n--- ENTERING LIVE POLLING PHASE ---")
    while True:
        try:
            # Wait for the next minute candle to form
            print(f"Waiting 60 seconds for the next candle update...")
            time.sleep(60) 
            
            # 1. ONLY fetch today's data
            print(f"Fetching latest live data for {today_str}...")
            live_raw_data = safe_fetch_market_data(auth_token, instruments, today_str)
            
            live_flat_list = []
            if live_raw_data and isinstance(live_raw_data, list):
                extract_flattened_data(live_raw_data, live_flat_list)
                
            if live_flat_list:
                live_df = process_into_dataframe(live_flat_list)
                
                # 2. Merge Live Data with Master Memory Buffer
                master_df = pd.concat([master_df, live_df])
                
                # 3. Drop duplicates (in case API returns overlapping minutes for today)
                master_df.drop_duplicates(subset=['Symbol', 'Timestamp'], keep='last', inplace=True)
                
                # Optional Memory Management: Keep only the last 5000 rows per symbol to prevent RAM leaks
                master_df = master_df.groupby('Symbol').tail(5000).reset_index(drop=True)
                
                # 4. Instantly Calculate New SMA
                calculate_and_print_sma(master_df, TIMEFRAME, SMA_PERIOD, instruments)
                
        except KeyboardInterrupt:
            print("\nLive polling stopped manually.")
            break
        except Exception as e:
            print(f"Error in live loop: {e}")
            time.sleep(10) # Brief pause on unexpected errors