import os
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_instrument_list, get_1MARKET_DATA
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Configuration & Authentication
# ---------------------------------------------------------
username = 'kumarroshanjha004@outlook.com'
password = 'Roshan@123'

DEFAULT_DATA_DIR = r"C:\Users\kumar\OneDrive\Desktop\Sample App"
SYMBOLS_FILE = os.path.join(DEFAULT_DATA_DIR, "symbol.txt")

auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")

# ---------------------------------------------------------
# 2. Helper Functions
# ---------------------------------------------------------

def get_instrument_from_file(filepath):
    """Reads the instrument code from the text file."""
    try:
        with open(filepath, 'r') as file:
            # .strip() removes any accidental spaces or newlines in the file
            return file.read().strip() 
    except FileNotFoundError:
        print(f"Error: Could not find the file at {filepath}")
        return None



def find_highest_5m_volume(data_list):
    """Converts a combined list of 1m data to 5m candles and finds the max volume."""
    
    if not data_list:
        print("No data received across the 3 days.")
        return None, None
        
    # 2. Define columns based on your provided data format
    columns = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
    
    # 3. Create the Pandas DataFrame
    df = pd.DataFrame(data_list, columns=columns)
    
    # 4. Clean the Timestamp 
    df['Timestamp'] = df['Timestamp'].str.replace(' ', '')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d%H:%M:%S')
    
    # 5. Convert price and volume columns from strings to floats
    cols_to_numeric = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric)
    
    # 6. Set the Timestamp as the index
    df.set_index('Timestamp', inplace=True)
    
    # 7. Resample into 5-minute candles
    df_5m = df.resample('5min').agg({
        'Open': 'first',   
        'High': 'max',     
        'Low': 'min',      
        'Close': 'last',   
        'Volume': 'sum'    
    }).dropna()            
    
    # 8. Find the highest volume and its timestamp
    max_volume = df_5m['Volume'].max()
    max_vol_time = df_5m['Volume'].idxmax()
    
    return max_volume, max_vol_time


# ---------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------

# Read the instrument from symbol.txt
instrument = get_instrument_from_file(SYMBOLS_FILE)

if instrument and auth_token:
    instruments = [instrument]  
    
    target_date_str = "2026-06-03"
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    dates_to_fetch = [
        (target_date - timedelta(days=2)).strftime("%Y-%m-%d"),
        (target_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        target_date.strftime("%Y-%m-%d")
    ]

    print(f"Instrument: {instrument}")
    print(f"Scanning 3-Day Window: {dates_to_fetch}\n")

    all_combined_data = []

    for d in dates_to_fetch:
        print(f"Fetching 1-minute ticks for: {d}...")
        result = get_1MARKET_DATA(auth_token, instruments, d)
        
        # Check if we got valid data back
        if result and len(result) > 0 and len(result[0]) > 0:
            # We use .extend() to add the rows into one massive list, rather than nesting them
            all_combined_data.extend(result[0])
        else:
            print(f"  -> No data found for {d}")
            
    print("\nData aggregation complete. Processing volume...\n")

    # 5. Process the massive combined list to find the highest 5-minute volume
    max_vol, max_time = find_highest_5m_volume(all_combined_data)
    
    if max_vol is not None:
        print("-" * 50)
        print(f"Highest 5-Minute Volume (Over 3 Days): {max_vol}")
        print(f"Occurred At: {max_time}")
        print("-" * 50)