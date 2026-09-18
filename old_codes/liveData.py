import os
from eqldata import DataClient, generate_auth_token, DataClient


username = 'kumarroshanjha004@outlook.com'
password = 'Roshan@123'


auth_token = generate_auth_token(username, password)

if auth_token:
    print("Authentication Successful.\n")


instrument_list = ["NSEEQ:RELIANCE"]

# def get_instrument_from_file(filepath):
#     """Reads the instrument code from the text file."""
#     try:
#         with open(filepath, 'r') as file:
#             # .strip() removes any accidental spaces or newlines in the file
#             return file.read().strip() 
#     except FileNotFoundError:
#         print(f"Error: Could not find the file at {filepath}")
#         return None


client = DataClient(auth_token, instrument_list)

try:
    while True:
        response = client.listen()
        if response is not None:
            print("Received:", response)
        else:  
            print("No data received.")
except KeyboardInterrupt:
    client.stop_listening()
    client.disconnect()
