import os
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_EOD, get_instrument_list, get_1MARKET_DATA
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Configuration & Authentication
# ---------------------------------------------------------
username = 'support@teztrader.com'
password = '1XFBqsBTs0a6rimR'


auth_token = generate_auth_token(username, password)
if auth_token:
    print(auth_token)
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


def get_previous_trading_day(start_date):
    """Finds the most recent valid trading day strictly before the start_date."""
    current_date = start_date - timedelta(days=1)
    
    while True:
        date_str = current_date.strftime("%Y-%m-%d")
        is_weekend = current_date.weekday() >= 5
        is_holiday = date_str in NSE_HOLIDAYS_2026
        
        if not is_weekend and not is_holiday:
            return date_str
            
        current_date -= timedelta(days=1)



# ---------------------------------------------------------
# 3. Main Execution
# ---------------------------------------------------------
instruments = [
    "NSEEQ:SWIGGY",
]


today_str = "2026-09-09"
today_date = datetime.strptime(today_str, "%Y-%m-%d")

# Fetch the exact previous trading day dynamically
for_date = get_previous_trading_day(today_date)

print(f"Fetching EOD data for the last valid trading session: {for_date}...\n")

result = get_EOD(auth_token, instruments, for_date)

# ---------------------------------------------------------
# 4. Data Parsing & Formatting
# ---------------------------------------------------------
valid_eod_data = []

# Safely extract all stock data from the nested payload
def extract_eod(lst):
    for item in lst:
        if isinstance(item, list):
            # Checking if it's a valid data row (minimum columns + string symbol)
            if len(item) >= 6 and isinstance(item[0], str) and item[0] != 'No Data':
                valid_eod_data.append(item)
            else:
                extract_eod(item)

if result and isinstance(result, list):
    extract_eod(result)

# Calculate Pivots and Print Table
if not valid_eod_data:
    print("No valid data received for the specified date.")
else:
    print("=" * 115)
    print(f"{'SYMBOL':<15} | {'S4':>8} | {'S3':>8} | {'S2':>8} | {'S1':>8} | {'R1':>8} | {'R2':>8} | {'R3':>8} | {'R4':>8} |")
    print("=" * 115)
    
    for data in valid_eod_data:
        symbol = data[0]

        high = float(data[3])
        low = float(data[4])
        close = float(data[5])

        range_hl = high - low

        # Camarilla Formulas (All 8 Levels)
        r4 = close + (range_hl * (1.1 / 2))
        r3 = close + (range_hl * (1.1 / 4))
        r2 = close + (range_hl * (1.1 / 6))
        r1 = close + (range_hl * (1.1 / 12))

        s1 = close - (range_hl * (1.1 / 12))
        s2 = close - (range_hl * (1.1 / 6))
        s3 = close - (range_hl * (1.1 / 4))
        s4 = close - (range_hl * (1.1 / 2))

        # Print all values seamlessly
        print(f"{symbol:<15} | {s4:>8.2f} | {s3:>8.2f} | {s2:>8.2f} | {s1:>8.2f} | {r1:>8.2f} | {r2:>8.2f} | {r3:>8.2f} | {r4:>8.2f} |")
        
    print("=" * 115)