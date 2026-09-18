import time
import asyncio

import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import os
import json

from eqldata import get_1MARKET_DATA, get_EOD, generate_auth_token



username = 'way2laabhacademy@gmail.com'
password = 'OnFfaS91zzujHq8u'


auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")


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



NSE_HOLIDAYS = {
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26",
    "2026-03-31", "2026-04-03", "2026-04-14", "2026-05-01",
    "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02",
    "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"
}

def get_previous_trading_day(current_date):
    """Steps back one day at a time, skipping weekends and holidays."""
    current_date -= timedelta(days=1)
    while current_date.weekday() >= 5 or current_date.strftime("%Y-%m-%d") in NSE_HOLIDAYS:
        current_date -= timedelta(days=1)
    return current_date


def get_last_n_trading_days(start_date, n_days):
    """Walks backward through time to find valid trading dates, skipping weekends/holidays."""
    valid_dates = []
    current_date = start_date
    while len(valid_dates) < n_days:
        date_str = current_date.strftime("%Y-%m-%d")
        is_weekend = current_date.weekday() >= 5
        if not is_weekend and date_str not in NSE_HOLIDAYS:
            valid_dates.append(date_str)
        current_date -= timedelta(days=1)
    return valid_dates


def safe_fetch_market_data(token, instrument_list, target_date_str):
    """Safely fetches 1-min data with rate-limit handling."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date_str)
            if isinstance(result, list) and len(result) > 0:
                return result
            if "too many requests" in str(result).lower() or "429" in str(result).lower():
                time.sleep(10)
                continue
            return result
        except Exception as e:
            print(f" [X] Error fetching data: {e}")
            return None
    return None


def extract_flattened_data(nested_list, master_list):
    """Flattens nested API responses into a single list of rows."""
    for item in nested_list:
        if isinstance(item, list):
            if len(item) >= 7 and isinstance(item[0], str) and item[0] != 'No Data':
                master_list.append(item)
            else:
                extract_flattened_data(item, master_list)


# Fetching Camrilla Points and Volume Breakouts
def bootstrap_camrilla_volume_breakouts(auth_token, instruments):
    """Fully synchronous method to calculate Pivots and Breakouts."""
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    today_str = now.strftime("%Y-%m-%d")
    print(f"🔍 Running Daily Analysis for {today_str}...")
    
    # 1. Determine Market Status
    is_weekend = now.weekday() >= 5
    is_holiday = today_str in NSE_HOLIDAYS
    # Run the heavy volume scanner ONLY if it's 09:20 AM or later
    is_pre_market = now.hour < 9 or (now.hour == 9 and now.minute < 20) 

    # ---------------------------------------------------------
    # Helper: Fetch EOD Data for Camarilla Pivots
    # ---------------------------------------------------------
    def fetch_prev_day_eod(target_date_str):
        max_retries = 3
        eod_dict = {}
        for attempt in range(max_retries):
            try:
                result = get_EOD(auth_token, instruments, target_date_str)
                if isinstance(result, list) and len(result) > 0:
                    def extract_eod(nested):
                        for item in nested:
                            if isinstance(item, list):
                                # EOD Format: ['SYMBOL', 'DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOL', 'VAL']
                                if len(item) >= 6 and isinstance(item[0], str) and item[0] != 'No Data':
                                    sym = item[0].split(":")[-1]
                                    try:
                                        eod_dict[sym] = {
                                            "high": float(item[3]),
                                            "low": float(item[4]),
                                            "close": float(item[5])
                                        }
                                    except ValueError:
                                        pass
                                else:
                                    extract_eod(item)
                    extract_eod(result)
                    break
                
                if "too many requests" in str(result).lower() or "429" in str(result).lower():
                    time.sleep(10)
                    continue
                else:
                    break 
                    
            except Exception as e:
                time.sleep(5)
        return eod_dict

    # 2. Fetch Previous Day's True High, Low, Close (ALWAYS RUNS)
    prev_date = get_previous_trading_day(now)
    prev_date_str = prev_date.strftime("%Y-%m-%d")
    eod_data = fetch_prev_day_eod(prev_date_str)

    # =========================================================
    # SCENARIO A: PRE-MARKET / HOLIDAY / WEEKEND (Lightweight)
    # =========================================================
    if is_weekend or is_holiday or is_pre_market:
        print("⚠️ Pre-Market/Holiday. Calculating EOD Camarilla Pivots, setting Volume Breakouts to null.")
        
        for symbol in instruments:
            clean_symbol = symbol.split(":")[-1]
            
            # --- A. Calculate Camarilla Pivots directly from EOD ---
            H4 = H3 = L3 = L4 = 0
            if clean_symbol in eod_data:
                sym_data = eod_data[clean_symbol]
                H = sym_data["high"]
                L = sym_data["low"]
                C = sym_data["close"]
                
                Range = H - L
                H4 = C + (Range * 1.1 / 2)
                H3 = C + (Range * 1.1 / 4)
                L3 = C - (Range * 1.1 / 4)
                L4 = C - (Range * 1.1 / 2)

            # --- C. Package & Push to Redis (with null volume breakout) ---
            payload = {
                "camarilla": {
                    "H4": round(H4, 2), "H3": round(H3, 2), 
                    "L3": round(L3, 2), "L4": round(L4, 2)
                },
                "volume_breakout": {
                    "is_breakout": None,
                    "today_first_5min_vol": None,
                    "past_3_days_max_vol": None,
                    "past_3_days_max_time": None
                },
                "updated_at": str(now)
            }
            # pipe.set(f"{clean_symbol}_daily_metrics", json.dumps(payload))
            
        # pipe.execute()
        print("✅ Pre-market Analysis Saved to Redis!")
        return True

    # =========================================================
    # SCENARIO B: ACTIVE MARKET >= 9:20 AM (Heavy Scanner)
    # =========================================================
    else:
        print("📈 Market is active. Fetching 1-min data for Volume Breakouts...")
        
        valid_dates = get_last_n_trading_days(now, 4)
        all_combined_data = []

        for date_str in valid_dates:
            raw_data = safe_fetch_market_data(auth_token, instruments, date_str)
            if raw_data:
                extract_flattened_data(raw_data, all_combined_data)
                
        if not all_combined_data:
            print("⚠️ No daily data fetched.")
            return False

        cols = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
        df = pd.DataFrame(all_combined_data).iloc[:, :7]
        df.columns = cols
        df['Timestamp'] = pd.to_datetime(df['Timestamp'].str.replace(' ', ''), format='%Y-%m-%d%H:%M:%S')
        df[cols[2:7]] = df[cols[2:7]].apply(pd.to_numeric)
        df.set_index('Timestamp', inplace=True)
        df.sort_index(inplace=True)

        for symbol in instruments:
            clean_symbol = symbol.split(":")[-1] 
            symbol_df = df[df['Symbol'] == clean_symbol]
            
            if symbol_df.empty:
                continue

            symbol_df = symbol_df.between_time('09:15', '15:29')
            if symbol_df.empty:
                continue

            # --- A. Camarilla Pivots (Calculated from accurate EOD) ---
            H4 = H3 = L3 = L4 = 0
            if clean_symbol in eod_data:
                sym_data = eod_data[clean_symbol]
                H = sym_data["high"]
                L = sym_data["low"]
                C = sym_data["close"]
                
                Range = H - L
                H4 = C + (Range * 1.1 / 2)
                H3 = C + (Range * 1.1 / 4)
                L3 = C - (Range * 1.1 / 4)
                L4 = C - (Range * 1.1 / 2)

            # --- B. 5-Min Volume Breakout Scanner ---
            resampled_5m = symbol_df.resample('5min', closed='left', label='left').agg({'Volume': 'sum'}).dropna()

            today_df = resampled_5m[resampled_5m.index.strftime('%Y-%m-%d') == today_str]
            hist_df = resampled_5m[resampled_5m.index.strftime('%Y-%m-%d') != today_str]
            
            print("✅✅✅✅✅✅✅✅✅")
            print(today_df)
            print(hist_df)
            print("✅✅✅✅✅✅✅✅✅")

            if not today_df.empty and not hist_df.empty:
                target_candle_time = f"{today_str} 09:15:00"
                if target_candle_time in today_df.index:
                    today_first_vol = float(today_df.loc[target_candle_time]['Volume'])
                else:
                    today_first_vol = float(today_df.iloc[0]['Volume'])
                    
                hist_max_vol = float(hist_df['Volume'].max())
                hist_max_time = str(hist_df['Volume'].idxmax())
                is_breakout = today_first_vol > hist_max_vol
            else:
                today_first_vol = 0
                hist_max_vol = 0
                hist_max_time = "N/A"
                is_breakout = False

            # --- C. Package & Push to Redis ---
            payload = {
                "camarilla": {
                    "H4": round(H4, 2), "H3": round(H3, 2), 
                    "L3": round(L3, 2), "L4": round(L4, 2)
                },
                "volume_breakout": {
                    "is_breakout": is_breakout,
                    "today_first_5min_vol": today_first_vol,
                    "past_3_days_max_vol": hist_max_vol,
                    "past_3_days_max_time": hist_max_time
                },
                "updated_at": str(now)
            }
            
            print(payload)

            # pipe.set(f"{clean_symbol}_daily_metrics", json.dumps(payload))

        # pipe.execute()
        print("✅ Active Market Analysis (Pivots & Breakouts) Saved to Redis!")
        return True


bootstrap_camrilla_volume_breakouts(auth_token, instruments)