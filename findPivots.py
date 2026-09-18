import os
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_EOD, get_instrument_list, get_1MARKET_DATA
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


today_str = "2026-06-04"
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
    print("=" * 39)
    print(f"{'SYMBOL':<15} | {'R1':>8} | {'S1':>8} |")
    print("=" * 39)
    
    for data in valid_eod_data:
        symbol = data[0]

        high = float(data[3])
        low = float(data[4])
        close = float(data[5])

        pivot_point = (high + low + close) / 3

        # Camarilla Formulas (All 8 Levels)
        
        r1 = (2 * pivot_point) - low
        s1 = (2 * pivot_point) - high
        
        # Print all values seamlessly
        print(f"{symbol:<15} | {r1:>8.2f} | {s1:>8.2f} |")
        
    print("=" * 39)