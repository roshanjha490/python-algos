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
START_DATE = "2025-01-01"          # Format: YYYY-MM-DD
END_DATE = datetime.today().strftime('%Y-%m-%d') 

# Brick Sizes
RENKO_BRICK_PCT_3M = 0.103
RENKO_BRICK_PCT_1M = 0.036

# --- PREVIOUS DAY RENKO ANCHORS (Just before START_DATE) ---
# Anchor for 3-minute Renko
PREV_LAST_BRICK_CLOSE_3M = 24078.60  
PREV_LAST_BRICK_DIR_3M = 'UP'       

# Anchor for 1-minute Renko
PREV_LAST_BRICK_CLOSE_1M = 24073.20
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

