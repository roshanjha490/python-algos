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


instruments = [
    "NSEEQ:20MICRONS",
    "NSEEQ:21STCENMGM"
]

for_date = "2026-06-05"

result = get_1MARKET_DATA(auth_token, instruments, for_date)
print(result)