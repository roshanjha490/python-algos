import os
from eqldata import DataClient, generate_auth_token, DataClient


username = 'support@teztrader.com'
password = '1XFBqsBTs0a6rimR'


auth_token = generate_auth_token(username, password)

if auth_token:
    print("Authentication Successful.\n")
else:
    print(auth_token)

instruments = [
    "NSEEQ:RELIANCE"
]


# def get_instrument_from_file(filepath):
#     """Reads the instrument code from the text file."""
#     try:
#         with open(filepath, 'r') as file:
#             # .strip() removes any accidental spaces or newlines in the file
#             return file.read().strip() 
#     except FileNotFoundError:
#         print(f"Error: Could not find the file at {filepath}")
#         return None


client = DataClient(auth_token, instruments)


try:
    while True:
        response = client.listen()
        if response:
            print("Received:", response)
        else:  
            print("No data received.")
except KeyboardInterrupt:
    client.stop_listening()
    client.disconnect()