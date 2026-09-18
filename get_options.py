import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from eqldata import generate_auth_token, get_EOD, get_instrument_list

# =====================================================================
# 1. Configuration & Authentication
# =====================================================================
USERNAME = "support@teztrader.com"
PASSWORD = "1XFBqsBTs0a6rimR"

auth_token = generate_auth_token(USERNAME, PASSWORD)
if not auth_token:
    raise ConnectionError("Authentication failed.")

# =====================================================================
# 2. Trading Calendar & Previous Date Function
# =====================================================================
NSE_HOLIDAYS_2026 = {
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31",
    "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28", "2026-06-26",
    "2026-09-14", "2026-10-02", "2026-10-20", "2026-11-10", "2026-11-24", "2026-12-25"
}

def get_previous_trading_day(reference_date: datetime) -> str:
    curr = reference_date - timedelta(days=1)
    while True:
        d_str = curr.strftime("%Y-%m-%d")
        if curr.weekday() < 5 and d_str not in NSE_HOLIDAYS_2026:
            return d_str
        curr -= timedelta(days=1)

# =====================================================================
# 3. Parse Instrument List
# =====================================================================
all_instruments_data = get_instrument_list(auth_token)
OPT_REGEX = re.compile(r"^NFOOPTSTK:(.+?)(\d{2}[A-Z]{3})_(\d+(?:\.\d+)?)(CE|PE)$")

options_by_stock = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

# Safely extract the list of strings from the dictionary structure
if isinstance(all_instruments_data, dict):
    # Grab the NFO Options list directly based on the JSON structure
    instrument_list = all_instruments_data.get("NFOOPTSTK", [])
elif isinstance(all_instruments_data, list):
    # Fallback just in case the API returns a flat list occasionally
    instrument_list = all_instruments_data
else:
    instrument_list = []

print(f"Found {len(instrument_list)} raw options symbols to parse.")

for symbol in instrument_list:
    match = OPT_REGEX.match(symbol)
    if match:
        underlying, expiry, strike_str, opt_type = match.groups()
        strike = float(strike_str)
        options_by_stock[underlying][expiry][strike][opt_type] = symbol

all_underlyings = sorted(options_by_stock.keys())
print(f"Successfully extracted {len(all_underlyings)} F&O underlyings.")


# =====================================================================
# 4. Fetch EOD Prices
# =====================================================================
ref_date = datetime.strptime("2026-09-18", "%Y-%m-%d")
trade_date = get_previous_trading_day(ref_date)
print(f"Fetching EOD spot prices for {trade_date} in batches...")

equity_symbols = [f"NSEEQ:{u}" for u in all_underlyings]
ltp_map = {}

def extract_close_prices(node):
    if isinstance(node, list):
        # Identify a valid data row (string symbol + data columns)
        if len(node) >= 6 and isinstance(node[0], str) and node[0] != 'No Data':
            sym = node[0]
            # Handle both "NSEEQ:RELIANCE" and "RELIANCE" formats
            stock_code = sym.split("NSEEQ:")[1] if "NSEEQ:" in sym else sym
            
            # If the parsed symbol is one of our F&O stocks, grab the close price
            if stock_code in all_underlyings:
                try:
                    ltp_map[stock_code] = float(node[5])
                except (ValueError, TypeError):
                    pass
        else:
            # Recursively search nested lists
            for child in node:
                extract_close_prices(child)

# Chunk requests into batches of 50 to prevent API failure
chunk_size = 50
for i in range(0, len(equity_symbols), chunk_size):
    batch = equity_symbols[i:i + chunk_size]
    raw_eod = get_EOD(auth_token, batch, trade_date)
    
    if raw_eod:
        extract_close_prices(raw_eod)

print(f"Successfully mapped LTP for {len(ltp_map)} / {len(all_underlyings)} stocks.")

# =====================================================================
# 5. Extract 7 Strikes Around ATM and Flatten
# =====================================================================
flat_symbol_list = []

for underlying, expiries in options_by_stock.items():
    if underlying not in ltp_map:
        continue

    spot_price = ltp_map[underlying]
    target_expiry = "26SEP" if "26SEP" in expiries else sorted(expiries.keys())[0]
    strike_dict = expiries[target_expiry]
    available_strikes = sorted(strike_dict.keys())

    if len(available_strikes) < 7:
        selected_strikes = available_strikes
    else:
        atm_strike = min(available_strikes, key=lambda s: abs(s - spot_price))
        atm_idx = available_strikes.index(atm_strike)

        start_idx = max(0, atm_idx - 3)
        end_idx = start_idx + 7

        if end_idx > len(available_strikes):
            end_idx = len(available_strikes)
            start_idx = max(0, end_idx - 7)

        selected_strikes = available_strikes[start_idx:end_idx]

    # Append to the flat list
    for s in selected_strikes:
        if "CE" in strike_dict[s]:
            flat_symbol_list.append(strike_dict[s]["CE"])
        if "PE" in strike_dict[s]:
            flat_symbol_list.append(strike_dict[s]["PE"])

# =====================================================================
# 6. Save Flat Output to JSON
# =====================================================================
output_filepath = "flat_options_list.json"
with open(output_filepath, "w") as f:
    json.dump(flat_symbol_list, f, indent=4)

print(f"Successfully saved {len(flat_symbol_list)} symbols to {output_filepath}")