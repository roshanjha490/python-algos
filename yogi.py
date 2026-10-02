import os
import time
import pandas as pd
from eqldata import DataClient, generate_auth_token, get_1MARKET_DATA, get_EOD
from datetime import datetime, timedelta, time as dtime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------
# 1. Configuration & Authentication
# ---------------------------------------------------------
username = 'kumarroshanjha786@gmail.com'
password = '7CjFjKHy62m94xD3'

auth_token = generate_auth_token(username, password)
if auth_token:
    print("Authentication Successful.\n")
else:
    print(auth_token)
    print("Authentication Failed. Please check your credentials.")
    exit(1)

# ---------------------------------------------------------
# 2. Smart Trading Calendar (2026)
# ---------------------------------------------------------
NSE_HOLIDAYS_2026 = {
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26",
    "2026-03-31", "2026-04-03", "2026-04-14", "2026-05-01",
    "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02",
    "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"
}

def get_last_n_trading_days(start_date, n_days):
    """Calculates the last 'n' valid trading days, skipping weekends and holidays."""
    valid_dates = []
    current_date = start_date

    while len(valid_dates) < n_days:
        date_str = current_date.strftime("%Y-%m-%d")
        is_weekend = current_date.weekday() >= 5
        is_holiday = date_str in NSE_HOLIDAYS_2026

        if not is_weekend and not is_holiday:
            valid_dates.append(date_str)

        current_date -= timedelta(days=1)

    return valid_dates

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
# 3. Rate-Limit Wrapper Functions
# ---------------------------------------------------------
def safe_fetch_market_data(token, instrument_list, target_date):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_1MARKET_DATA(token, instrument_list, target_date)
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result

            result_str = str(result).lower()
            if "too many requests" in result_str or "429" in result_str:
                print(f" [!] Intraday Rate Limited. Waiting 30s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(30)
                continue

            return result
        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str:
                print(f" [!] Intraday Rate Limited (Exception). Waiting 30s...")
                time.sleep(30)
                continue
            else:
                print(f" [X] Unexpected Intraday API Error: {e}")
                return None
    return None

def safe_fetch_eod_data(token, instrument_list, target_date):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_EOD(token, instrument_list, target_date)
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                return result

            result_str = str(result).lower()
            if "too many requests" in result_str or "429" in result_str:
                print(f" [!] EOD Rate Limited. Waiting 30s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(30)
                continue

            return result
        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str:
                print(f" [!] EOD Rate Limited (Exception). Waiting 30s...")
                time.sleep(30)
                continue
            else:
                print(f" [X] Unexpected EOD API Error: {e}")
                return None
    return None


# ---------------------------------------------------------
# 4. Open=High / Open=Low Breakout Logic with EOD Confirmation
# ---------------------------------------------------------
HIGH_TARGET_PCT = 0.01   # 1% target for Open=High breakout (LONG)
LOW_TARGET_PCT = 0.01    # 1% target for Open=Low breakout (SHORT)

# Breakout/breakdown checks only start from this time of day onward.
BREAKOUT_CHECK_TIME = dtime(10, 0, 0)

def process_bulk_data(data_list, eod_cache):
    if not data_list:
        print("No valid intraday data received to process.")
        return

    columns = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Extra']
    df = pd.DataFrame(data_list, columns=columns)

    df['Timestamp'] = df['Timestamp'].str.replace(' ', '')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d%H:%M:%S')

    cols_to_numeric = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric)

    df['Date'] = df['Timestamp'].dt.date
    results = []
    grouped = df.groupby(['Symbol', 'Date'])

    for (symbol, date), group_df in grouped:
        
        # Determine previous day's candle color via EOD cache
        prev_date_str = get_previous_trading_day(date)
        prev_eod = eod_cache.get(prev_date_str, {}).get(symbol)
        
        # If we couldn't fetch EOD data for the prior day, skip trading this symbol today
        if not prev_eod:
            continue
            
        prev_open = prev_eod['Open']
        prev_close = prev_eod['Close']
        
        is_prev_green = prev_close > prev_open
        is_prev_red = prev_close < prev_open

        # Proceed with Intraday Analysis
        min1 = group_df.set_index('Timestamp').sort_index()
        if min1.empty:
            continue

        df_5m = min1.resample('5min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()

        if df_5m.empty:
            continue

        f_open = df_5m.iloc[0]['Open']
        f_high = df_5m.iloc[0]['High']
        f_low = df_5m.iloc[0]['Low']

        check_start_time = pd.Timestamp.combine(min1.index[0].date(), BREAKOUT_CHECK_TIME)
        subsequent_5m = df_5m[df_5m.index >= check_start_time]
        
        if subsequent_5m.empty:
            continue

        last_close = min1.iloc[-1]['Close']
        last_time = min1.index[-1]

        # ---------------- Condition 1: Open == High & Prev Day Green -> LONG ----------------
        if f_open == f_high == prev_close and is_prev_green:
            breakout_candles = subsequent_5m[subsequent_5m['Close'] > f_high]
            if not breakout_candles.empty:
                entry_time = breakout_candles.index[0]
                entry_price = f_high
                target_price = entry_price * (1 + HIGH_TARGET_PCT)

                after_entry = subsequent_5m[subsequent_5m.index > entry_time]
                target_hits = after_entry[after_entry['High'] >= target_price]

                if not target_hits.empty:
                    exit_time = target_hits.index[0]
                    exit_price = target_price
                    exit_reason = f"Target {HIGH_TARGET_PCT*100:.0f}% Hit"
                else:
                    exit_time = last_time
                    exit_price = last_close
                    exit_reason = "EOD Close (Target Not Hit)"

                pnl_points = exit_price - entry_price
                pnl_pct = (pnl_points / entry_price) * 100

                results.append({
                    'Date': str(date), 'Symbol': symbol, 'Condition': 'Open=High (LONG)',
                    'First_Open': f_open, 'First_High/Low': f_high,
                    'Entry_Time': entry_time.strftime('%H:%M'), 'Entry_Price': entry_price,
                    'Exit_Time': exit_time.strftime('%H:%M'), 'Exit_Price': exit_price,
                    'Exit_Reason': exit_reason,
                    'PnL_Points': pnl_points, 'PnL_Pct': pnl_pct
                })

        # ---------------- Condition 2: Open == Low & Prev Day Red -> SHORT ----------------
        if f_open == f_low == prev_close and is_prev_red:
            breakdown_candles = subsequent_5m[subsequent_5m['Close'] < f_low]
            if not breakdown_candles.empty:
                entry_time = breakdown_candles.index[0]
                entry_price = f_low
                target_price = entry_price * (1 - LOW_TARGET_PCT)

                after_entry = subsequent_5m[subsequent_5m.index > entry_time]
                target_hits = after_entry[after_entry['Low'] <= target_price]

                if not target_hits.empty:
                    exit_time = target_hits.index[0]
                    exit_price = target_price
                    exit_reason = f"Target {LOW_TARGET_PCT*100:.0f}% Hit"
                else:
                    exit_time = last_time
                    exit_price = last_close
                    exit_reason = "EOD Close (Target Not Hit)"

                pnl_points = entry_price - exit_price
                pnl_pct = (pnl_points / entry_price) * 100

                results.append({
                    'Date': str(date), 'Symbol': symbol, 'Condition': 'Open=Low (SHORT)',
                    'First_Open': f_open, 'First_High/Low': f_low,
                    'Entry_Time': entry_time.strftime('%H:%M'), 'Entry_Price': entry_price,
                    'Exit_Time': exit_time.strftime('%H:%M'), 'Exit_Price': exit_price,
                    'Exit_Reason': exit_reason,
                    'PnL_Points': pnl_points, 'PnL_Pct': pnl_pct
                })

    # ---------------- Print nicely formatted results ----------------
    print("\n" + "=" * 150)
    print(f" {'Date':<12} | {'Symbol':<14} | {'Condition':<20} | {'Entry Time':<10} | {'Entry Px':<10} | "
          f"{'Exit Time':<9} | {'Exit Px':<10} | {'Exit Reason':<26} | {'PnL(pts)':<10} | {'PnL(%)'}")
    print("=" * 150)

    results = sorted(results, key=lambda x: (x['Date'], x['Symbol']))
    total_pnl_points = 0.0
    wins = 0

    for res in results:
        total_pnl_points += res['PnL_Points']
        if res['PnL_Points'] > 0:
            wins += 1
        print(f" {res['Date']:<12} | {res['Symbol']:<14} | {res['Condition']:<20} | "
              f"{res['Entry_Time']:<10} | {res['Entry_Price']:<10.2f} | {res['Exit_Time']:<9} | "
              f"{res['Exit_Price']:<10.2f} | {res['Exit_Reason']:<26} | "
              f"{res['PnL_Points']:<10.2f} | {res['PnL_Pct']:.2f}%")

    print("=" * 150)
    print(f"Total Trades Found: {len(results)}")
    if results:
        print(f"Winning Trades: {wins} | Losing/BE Trades: {len(results) - wins}")
        print(f"Total PnL (points, per 1 unit/share): {total_pnl_points:.2f}")
        print(f"Average PnL per trade (points): {total_pnl_points/len(results):.2f}")
    print()

    export_results_to_excel(results, total_pnl_points, wins)


def export_results_to_excel(results, total_pnl_points, wins):
    if not results:
        print("No trades to export — skipping Excel file.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Trade Log"
    headers = [
        "Date", "Symbol", "Condition", "First_Open", "First_High/Low",
        "Entry_Time", "Entry_Price", "Exit_Time", "Exit_Price",
        "Exit_Reason", "PnL_Points", "PnL_Pct"
    ]

    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    body_font = Font(name="Arial")
    win_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    loss_fill = PatternFill(start_color="FCE4E4", end_color="FCE4E4", fill_type="solid")

    ws.append(headers)
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for res in results:
        row = [
            res['Date'], res['Symbol'], res['Condition'], res['First_Open'],
            res['First_High/Low'], res['Entry_Time'], res['Entry_Price'],
            res['Exit_Time'], res['Exit_Price'], res['Exit_Reason'],
            round(res['PnL_Points'], 2), round(res['PnL_Pct'], 2)
        ]
        ws.append(row)
        row_idx = ws.max_row
        fill = win_fill if res['PnL_Points'] > 0 else loss_fill
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = body_font
            cell.fill = fill

    summary_row_start = ws.max_row + 2
    summary_lines = [
        ("Total Trades", len(results)),
        ("Winning Trades", wins),
        ("Losing/BE Trades", len(results) - wins),
        ("Total PnL (points, per 1 unit/share)", round(total_pnl_points, 2)),
        ("Average PnL per Trade (points)", round(total_pnl_points / len(results), 2)),
    ]
    for i, (label, value) in enumerate(summary_lines):
        r = summary_row_start + i
        ws.cell(row=r, column=1, value=label).font = Font(name="Arial", bold=True)
        ws.cell(row=r, column=2, value=value).font = Font(name="Arial")

    for col_idx, header in enumerate(headers, start=1):
        max_len = len(str(header))
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 3

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

    output_filename = f"breakout_trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = os.path.join(os.getcwd(), output_filename)
    wb.save(output_path)
    print(f"Trade log exported to Excel: {output_path}")


# ---------------------------------------------------------
# 5. Main Execution
# ---------------------------------------------------------
instruments = [
    "NSEEQ:360ONE", "NSEEQ:ABB", "NSEEQ:APLAPOLLO", "NSEEQ:AUBANK", "NSEEQ:ADANIENSOL",
    "NSEEQ:ADANIENT", "NSEEQ:ADANIGREEN", "NSEEQ:ADANIPORTS", "NSEEQ:ADANIPOWER", "NSEEQ:ABCAPITAL",
    "NSEEQ:ALKEM", "NSEEQ:AMBER", "NSEEQ:AMBUJACEM", "NSEEQ:ANGELONE", "NSEEQ:APOLLOHOSP",
    "NSEEQ:ASHOKLEY", "NSEEQ:ASIANPAINT", "NSEEQ:ASTRAL", "NSEEQ:AUROPHARMA", "NSEEQ:DMART",
    "NSEEQ:AXISBANK", "NSEEQ:BSE", "NSEEQ:BAJAJ_AUTO", "NSEEQ:BAJFINANCE", "NSEEQ:BAJAJFINSV",
    "NSEEQ:BAJAJHLDNG", "NSEEQ:BANDHANBNK", "NSEEQ:BANKBARODA", "NSEEQ:BANKINDIA", "NSEEQ:BDL",
    "NSEEQ:BEL", "NSEEQ:BHARATFORG", "NSEEQ:BHEL", "NSEEQ:BPCL", "NSEEQ:BHARTIARTL",
    "NSEEQ:BIOCON", "NSEEQ:BLUESTARCO", "NSEEQ:BOSCHLTD", "NSEEQ:BRITANNIA", "NSEEQ:CGPOWER",
    "NSEEQ:CANBK", "NSEEQ:CDSL", "NSEEQ:CHOLAFIN", "NSEEQ:CIPLA", "NSEEQ:COALINDIA",
    "NSEEQ:COCHINSHIP", "NSEEQ:COFORGE", "NSEEQ:COLPAL", "NSEEQ:CAMS", "NSEEQ:CONCOR",
    "NSEEQ:CROMPTON", "NSEEQ:CUMMINSIND", "NSEEQ:DLF", "NSEEQ:DABUR", "NSEEQ:DALBHARAT",
    "NSEEQ:DELHIVERY", "NSEEQ:DIVISLAB", "NSEEQ:DIXON", "NSEEQ:DRREDDY", "NSEEQ:ETERNAL",
    "NSEEQ:EICHERMOT", "NSEEQ:EXIDEIND", "NSEEQ:FORCEMOT", "NSEEQ:NYKAA", "NSEEQ:FORTIS",
    "NSEEQ:GAIL", "NSEEQ:GVT_D", "NSEEQ:GMRAIRPORT", "NSEEQ:GLENMARK", "NSEEQ:GODFRYPHLP",
    "NSEEQ:GODREJCP", "NSEEQ:GODREJPROP", "NSEEQ:GRASIM", "NSEEQ:HCLTECH", "NSEEQ:HDFCAMC",
    "NSEEQ:HDFCBANK", "NSEEQ:HDFCLIFE", "NSEEQ:HAVELLS", "NSEEQ:HEROMOTOCO", "NSEEQ:HINDALCO",
    "NSEEQ:HAL", "NSEEQ:HINDPETRO", "NSEEQ:HINDUNILVR", "NSEEQ:HINDZINC", "NSEEQ:POWERINDIA",
    "NSEEQ:HYUNDAI", "NSEEQ:ICICIBANK", "NSEEQ:ICICIGI", "NSEEQ:ICICIPRULI", "NSEEQ:IDFCFIRSTB",
    "NSEEQ:ITC", "NSEEQ:INDIANB", "NSEEQ:IEX", "NSEEQ:IOC", "NSEEQ:IRFC", "NSEEQ:IREDA",
    "NSEEQ:INDUSTOWER", "NSEEQ:INDUSINDBK", "NSEEQ:NAUKRI", "NSEEQ:INFY", "NSEEQ:INOXWIND",
    "NSEEQ:INDIGO", "NSEEQ:JINDALSTEL", "NSEEQ:JSWENERGY", "NSEEQ:JSWSTEEL", "NSEEQ:JIOFIN",
    "NSEEQ:JUBLFOOD", "NSEEQ:KEI", "NSEEQ:KPITTECH", "NSEEQ:KALYANKJIL", "NSEEQ:KAYNES",
    "NSEEQ:KFINTECH", "NSEEQ:KOTAKBANK", "NSEEQ:LTF", "NSEEQ:LICHSGFIN", "NSEEQ:LTM",
    "NSEEQ:LT", "NSEEQ:LAURUSLABS", "NSEEQ:LICI", "NSEEQ:LODHA", "NSEEQ:LUPIN", "NSEEQ:M_M",
    "NSEEQ:MANAPPURAM", "NSEEQ:MANKIND", "NSEEQ:MARICO", "NSEEQ:MARUTI", "NSEEQ:MFSL",
    "NSEEQ:MAXHEALTH", "NSEEQ:MAZDOCK", "NSEEQ:MOTILALOFS", "NSEEQ:MPHASIS", "NSEEQ:MCX",
    "NSEEQ:MUTHOOTFIN", "NSEEQ:NBCC", "NSEEQ:NHPC", "NSEEQ:NMDC", "NSEEQ:NTPC", "NSEEQ:NATIONALUM",
    "NSEEQ:NESTLEIND", "NSEEQ:NAM_INDIA", "NSEEQ:NUVAMA", "NSEEQ:OBEROIRLTY", "NSEEQ:ONGC",
    "NSEEQ:OIL", "NSEEQ:PAYTM", "NSEEQ:OFSS", "NSEEQ:POLICYBZR", "NSEEQ:PGEL", "NSEEQ:PIIND",
    "NSEEQ:PNBHOUSING", "NSEEQ:PAGEIND", "NSEEQ:PATANJALI", "NSEEQ:PERSISTENT", "NSEEQ:PETRONET",
    "NSEEQ:PIDILITIND", "NSEEQ:POLYCAB", "NSEEQ:PFC", "NSEEQ:POWERGRID", "NSEEQ:PREMIERENE",
    "NSEEQ:PRESTIGE", "NSEEQ:PNB", "NSEEQ:RBLBANK", "NSEEQ:RECLTD", "NSEEQ:RADICO", "NSEEQ:RVNL",
    "NSEEQ:RELIANCE", "NSEEQ:SBICARD", "NSEEQ:SBILIFE", "NSEEQ:SHREECEM", "NSEEQ:SRF",
    "NSEEQ:SAMMAANCAP", "NSEEQ:MOTHERSON", "NSEEQ:SHRIRAMFIN", "NSEEQ:SIEMENS", "NSEEQ:SOLARINDS",
    "NSEEQ:SONACOMS", "NSEEQ:SBIN", "NSEEQ:SAIL", "NSEEQ:SUNPHARMA", "NSEEQ:SUPREMEIND",
    "NSEEQ:SUZLON", "NSEEQ:SWIGGY", "NSEEQ:TATACONSUM", "NSEEQ:TVSMOTOR", "NSEEQ:TCS",
    "NSEEQ:TATAELXSI", "NSEEQ:TMPV", "NSEEQ:TATAPOWER", "NSEEQ:TATASTEEL", "NSEEQ:TECHM",
    "NSEEQ:FEDERALBNK", "NSEEQ:INDHOTEL", "NSEEQ:PHOENIXLTD", "NSEEQ:TITAN", "NSEEQ:TORNTPHARM",
    "NSEEQ:TRENT", "NSEEQ:TIINDIA", "NSEEQ:UNOMINDA", "NSEEQ:UPL", "NSEEQ:ULTRACEMCO",
    "NSEEQ:UNIONBANK", "NSEEQ:UNITDSPR", "NSEEQ:VBL", "NSEEQ:VEDL", "NSEEQ:VMM", "NSEEQ:IDEA",
    "NSEEQ:VOLTAS", "NSEEQ:WAAREEENER", "NSEEQ:WIPRO", "NSEEQ:YESBANK", "NSEEQ:ZYDUSLIFE",
]

if auth_token:
    all_combined_data = []
    eod_cache = {}
    today = datetime.now()

    # Ask for 22 days (Roughly 1 trading month of history)
    target_dates = get_last_n_trading_days(today, 7)

    print(f"Calculated Valid Trading Days: {target_dates}\n")
    print(f"Starting fetch for {len(instruments)} instruments...")

    for target_date in target_dates:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        prev_date_str = get_previous_trading_day(target_dt)

        # ---------------- 1. Fetch EOD for the previous trading day ----------------
        if prev_date_str not in eod_cache:
            print(f"[{target_date}] Fetching EOD data for previous day: {prev_date_str}...")
            eod_result = safe_fetch_eod_data(auth_token, instruments, prev_date_str)
            eod_data_parsed = {}

            def extract_eod(lst):
                for item in lst:
                    if isinstance(item, list):
                        if len(item) >= 6 and isinstance(item[0], str) and item[0] != 'No Data':
                            sym = item[0]
                            try:
                                op = float(item[2])
                                cl = float(item[5])
                                eod_data_parsed[sym] = {'Open': op, 'Close': cl}
                            except ValueError:
                                pass
                        else:
                            extract_eod(item)

            if eod_result and isinstance(eod_result, list):
                extract_eod(eod_result)

            # Store in cache so we don't refetch if overlapping
            eod_cache[prev_date_str] = eod_data_parsed

        # ---------------- 2. Fetch 1-min intraday data for target_date ----------------
        print(f"[{target_date}] Fetching 1-min Intraday data...")
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

    # Finally, process all loaded intraday data while passing our EOD cache dictionary down to it
    process_bulk_data(all_combined_data, eod_cache)