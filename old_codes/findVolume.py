import os
import time
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_instrument_list, get_1MARKET_DATA
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. Configuration & Authentication
# ---------------------------------------------------------
username = 'kumarroshanjha004@outlook.com'
password = 'Roshan@123'

auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")

# ---------------------------------------------------------
# 2. Smart Trading Calendar (2026)
# ---------------------------------------------------------
# Exact holiday dates provided, formatted as YYYY-MM-DD
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

def get_last_n_trading_days(start_date, n_days):
    """Calculates the last 'n' valid trading days, skipping weekends and holidays."""
    valid_dates = []
    current_date = start_date
    
    while len(valid_dates) < n_days:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # .weekday() returns 5 for Saturday and 6 for Sunday
        is_weekend = current_date.weekday() >= 5
        is_holiday = date_str in NSE_HOLIDAYS_2026
        
        if not is_weekend and not is_holiday:
            valid_dates.append(date_str)
            
        # Move back one day in time
        current_date -= timedelta(days=1)
        
    return valid_dates

# ---------------------------------------------------------
# 3. Rate-Limit Wrapper Function
# ---------------------------------------------------------
def safe_fetch_market_data(token, instrument_list, target_date):
    """Fetches data and handles 'Too Many Requests' gracefully."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date)
            
            # SAFEGUARD: If the result is a list containing lists, it's valid market data! 
            # Return it immediately so we don't accidentally scan prices/volumes for "429".
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result
            
            # If it's NOT valid market data, now we can safely check if it's an error message
            result_str = str(result).lower()
            if "too many requests" in result_str or "429" in result_str:
                print(f" [!] Rate Limited. Waiting 30 seconds (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(30)
                continue  # Try again
                
            # If it's just 'No Data' or a weekend, return it so the main loop can handle it
            return result

        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str:
                print(f" [!] Rate Limited (Exception). Waiting 30 seconds...")
                time.sleep(30)
                continue
            else:
                print(f" [X] Unexpected API Error: {e}")
                return None
                
    return None

# ---------------------------------------------------------
# 4. Pandas Processing
# ---------------------------------------------------------
def process_bulk_data(data_list):
    """Processes bulk ticks, groups by symbol, and calculates max volume."""
    if not data_list:
        print("No valid data received to process.")
        return
        
    columns = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
    df = pd.DataFrame(data_list, columns=columns)
    
    df['Timestamp'] = df['Timestamp'].str.replace(' ', '')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d%H:%M:%S')
    
    cols_to_numeric = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric)
    
    print("\n" + "="*50)
    print(" 📊 FINAL RESULTS ")
    print("="*50)
    
    grouped = df.groupby('Symbol')
    for symbol, group_df in grouped:
        group_df.set_index('Timestamp', inplace=True)
        df_5m = group_df.resample('5min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if not df_5m.empty:
            max_volume = df_5m['Volume'].max()
            max_vol_time = df_5m['Volume'].idxmax()
            print(f"🟢 {symbol:<15} | Max Vol: {max_volume:<10} | Time: {max_vol_time}")
        else:
            print(f"🔴 {symbol:<15} | No valid 5-minute candles formed.")
    print("="*50)

# ---------------------------------------------------------
# 5. Main Execution
# ---------------------------------------------------------
instruments = [
    "NSEEQ:360ONE",
    "NSEEQ:ABB",
    "NSEEQ:APLAPOLLO",
    "NSEEQ:AUBANK",
    "NSEEQ:ADANIENSOL",
    "NSEEQ:ADANIENT",
    "NSEEQ:ADANIGREEN",
    "NSEEQ:ADANIPORTS",
    "NSEEQ:ADANIPOWER",
    "NSEEQ:ABCAPITAL",
    "NSEEQ:ALKEM",
    "NSEEQ:AMBER",
    "NSEEQ:AMBUJACEM",
    "NSEEQ:ANGELONE",
    "NSEEQ:APOLLOHOSP",
    "NSEEQ:ASHOKLEY",
    "NSEEQ:ASIANPAINT",
    "NSEEQ:ASTRAL",
    "NSEEQ:AUROPHARMA",
    "NSEEQ:DMART",
    "NSEEQ:AXISBANK",
    "NSEEQ:BSE",
    "NSEEQ:BAJAJ_AUTO",
    "NSEEQ:BAJFINANCE",
    "NSEEQ:BAJAJFINSV",
    "NSEEQ:BAJAJHLDNG",
    "NSEEQ:BANDHANBNK",
    "NSEEQ:BANKBARODA",
    "NSEEQ:BANKINDIA",
    "NSEEQ:BDL",
    "NSEEQ:BEL",
    "NSEEQ:BHARATFORG",
    "NSEEQ:BHEL",
    "NSEEQ:BPCL",
    "NSEEQ:BHARTIARTL",
    "NSEEQ:BIOCON",
    "NSEEQ:BLUESTARCO",
    "NSEEQ:BOSCHLTD",
    "NSEEQ:BRITANNIA",
    "NSEEQ:CGPOWER",
    "NSEEQ:CANBK",
    "NSEEQ:CDSL",
    "NSEEQ:CHOLAFIN",
    "NSEEQ:CIPLA",
    "NSEEQ:COALINDIA",
    "NSEEQ:COCHINSHIP",
    "NSEEQ:COFORGE",
    "NSEEQ:COLPAL",
    "NSEEQ:CAMS",
    "NSEEQ:CONCOR",
    "NSEEQ:CROMPTON",
    "NSEEQ:CUMMINSIND",
    "NSEEQ:DLF",
    "NSEEQ:DABUR",
    "NSEEQ:DALBHARAT",
    "NSEEQ:DELHIVERY",
    "NSEEQ:DIVISLAB",
    "NSEEQ:DIXON",
    "NSEEQ:DRREDDY",
    "NSEEQ:ETERNAL",
    "NSEEQ:EICHERMOT",
    "NSEEQ:EXIDEIND",
    "NSEEQ:FORCEMOT",
    "NSEEQ:NYKAA",
    "NSEEQ:FORTIS",
    "NSEEQ:GAIL",
    "NSEEQ:GVT_D",
    "NSEEQ:GMRAIRPORT",
    "NSEEQ:GLENMARK",
    "NSEEQ:GODFRYPHLP",
    "NSEEQ:GODREJCP",
    "NSEEQ:GODREJPROP",
    "NSEEQ:GRASIM",
    "NSEEQ:HCLTECH",
    "NSEEQ:HDFCAMC",
    "NSEEQ:HDFCBANK",
    "NSEEQ:HDFCLIFE",
    "NSEEQ:HAVELLS",
    "NSEEQ:HEROMOTOCO",
    "NSEEQ:HINDALCO",
    "NSEEQ:HAL",
    "NSEEQ:HINDPETRO",
    "NSEEQ:HINDUNILVR",
    "NSEEQ:HINDZINC",
    "NSEEQ:POWERINDIA",
    "NSEEQ:HYUNDAI",
    "NSEEQ:ICICIBANK",
    "NSEEQ:ICICIGI",
    "NSEEQ:ICICIPRULI",
    "NSEEQ:IDFCFIRSTB",
    "NSEEQ:ITC",
    "NSEEQ:INDIANB",
    "NSEEQ:IEX",
    "NSEEQ:IOC",
    "NSEEQ:IRFC",
    "NSEEQ:IREDA",
    "NSEEQ:INDUSTOWER",
    "NSEEQ:INDUSINDBK",
    "NSEEQ:NAUKRI",
    "NSEEQ:INFY",
    "NSEEQ:INOXWIND",
    "NSEEQ:INDIGO",
    "NSEEQ:JINDALSTEL",
    "NSEEQ:JSWENERGY",
    "NSEEQ:JSWSTEEL",
    "NSEEQ:JIOFIN",
    "NSEEQ:JUBLFOOD",
    "NSEEQ:KEI",
    "NSEEQ:KPITTECH",
    "NSEEQ:KALYANKJIL",
    "NSEEQ:KAYNES",
    "NSEEQ:KFINTECH",
    "NSEEQ:KOTAKBANK",
    "NSEEQ:LTF",
    "NSEEQ:LICHSGFIN",
    "NSEEQ:LTM",
    "NSEEQ:LT",
    "NSEEQ:LAURUSLABS",
    "NSEEQ:LICI",
    "NSEEQ:LODHA",
    "NSEEQ:LUPIN",
    "NSEEQ:M_M",
    "NSEEQ:MANAPPURAM",
    "NSEEQ:MANKIND",
    "NSEEQ:MARICO",
    "NSEEQ:MARUTI",
    "NSEEQ:MFSL",
    "NSEEQ:MAXHEALTH",
    "NSEEQ:MAZDOCK",
    "NSEEQ:MOTILALOFS",
    "NSEEQ:MPHASIS",
    "NSEEQ:MCX",
    "NSEEQ:MUTHOOTFIN",
    "NSEEQ:NBCC",
    "NSEEQ:NHPC",
    "NSEEQ:NMDC",
    "NSEEQ:NTPC",
    "NSEEQ:NATIONALUM",
    "NSEEQ:NESTLEIND",
    "NSEEQ:NAM_INDIA",
    "NSEEQ:NUVAMA",
    "NSEEQ:OBEROIRLTY",
    "NSEEQ:ONGC",
    "NSEEQ:OIL",
    "NSEEQ:PAYTM",
    "NSEEQ:OFSS",
    "NSEEQ:POLICYBZR",
    "NSEEQ:PGEL",
    "NSEEQ:PIIND",
    "NSEEQ:PNBHOUSING",
    "NSEEQ:PAGEIND",
    "NSEEQ:PATANJALI",
    "NSEEQ:PERSISTENT",
    "NSEEQ:PETRONET",
    "NSEEQ:PIDILITIND",
    "NSEEQ:POLYCAB",
    "NSEEQ:PFC",
    "NSEEQ:POWERGRID",
    "NSEEQ:PREMIERENE",
    "NSEEQ:PRESTIGE",
    "NSEEQ:PNB",
    "NSEEQ:RBLBANK",
    "NSEEQ:RECLTD",
    "NSEEQ:RADICO",
    "NSEEQ:RVNL",
    "NSEEQ:RELIANCE",
    "NSEEQ:SBICARD",
    "NSEEQ:SBILIFE",
    "NSEEQ:SHREECEM",
    "NSEEQ:SRF",
    "NSEEQ:SAMMAANCAP",
    "NSEEQ:MOTHERSON",
    "NSEEQ:SHRIRAMFIN",
    "NSEEQ:SIEMENS",
    "NSEEQ:SOLARINDS",
    "NSEEQ:SONACOMS",
    "NSEEQ:SBIN",
    "NSEEQ:SAIL",
    "NSEEQ:SUNPHARMA",
    "NSEEQ:SUPREMEIND",
    "NSEEQ:SUZLON",
    "NSEEQ:SWIGGY",
    "NSEEQ:TATACONSUM",
    "NSEEQ:TVSMOTOR",
    "NSEEQ:TCS",
    "NSEEQ:TATAELXSI",
    "NSEEQ:TMPV",
    "NSEEQ:TATAPOWER",
    "NSEEQ:TATASTEEL",
    "NSEEQ:TECHM",
    "NSEEQ:FEDERALBNK",
    "NSEEQ:INDHOTEL",
    "NSEEQ:PHOENIXLTD",
    "NSEEQ:TITAN",
    "NSEEQ:TORNTPHARM",
    "NSEEQ:TRENT",
    "NSEEQ:TIINDIA",
    "NSEEQ:UNOMINDA",
    "NSEEQ:UPL",
    "NSEEQ:ULTRACEMCO",
    "NSEEQ:UNIONBANK",
    "NSEEQ:UNITDSPR",
    "NSEEQ:VBL",
    "NSEEQ:VEDL",
    "NSEEQ:VMM",
    "NSEEQ:IDEA",
    "NSEEQ:VOLTAS",
    "NSEEQ:WAAREEENER",
    "NSEEQ:WIPRO",
    "NSEEQ:YESBANK",
    "NSEEQ:ZYDUSLIFE",
]

if auth_token:
    all_combined_data = []
    today = datetime.now()
    
    # NEW LOGIC: Ask our smart calendar for exactly 3 valid trading days
    target_dates = get_last_n_trading_days(today, 3)
    
    print(f"Calculated Valid Trading Days: {target_dates}\n")
    print(f"Starting fetch for {len(instruments)} instruments...")
    
    # Loop exclusively through guaranteed trading days
    for target_date in target_dates:
        print(f"Fetching data for: {target_date}...")
        
        result = safe_fetch_market_data(auth_token, instruments, target_date)
        
        def extract_ticks(lst):
            for item in lst:
                if isinstance(item, list):
                    if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                        all_combined_data.append(item)
                    else:
                        extract_ticks(item)
                        
        if result and isinstance(result, list):
            extract_ticks(result)
            print(f" -> Current total ticks loaded: {len(all_combined_data)}")
        else:
            print(f" -> Unexpected empty response for {target_date}.")

    process_bulk_data(all_combined_data)