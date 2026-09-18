from getpass import getpass
from eqldata import generate_auth_token, get_instrument_list
import json # Added to handle saving the data structurally

username = 'kumarroshanjha786@gmail.com'
password = '7CjFjKHy62m94xD3'


auth_token = generate_auth_token(username, password)
instruments = get_instrument_list(auth_token)

print(type(instruments))
print(instruments)

# Option 1: Save as a JSON file (Recommended for API responses)
with open('instruments_list.json', 'w') as json_file:
    # indent=4 makes the file easily readable for humans
    json.dump(instruments, json_file, indent=4)
    print("Saved successfully to instruments_list.json")

# Option 2: Save as a plain text file (Useful if it's just a simple list of strings)
with open('instruments_list.txt', 'w') as txt_file:
    # Assuming 'instruments' is a list, we can write each item on a new line
    if isinstance(instruments, list):
        for item in instruments:
            txt_file.write(f"{item}\n")
        print("Saved successfully to instruments_list.txt")
    else:
        # If it's a dictionary or something else, just cast it to string
        txt_file.write(str(instruments))
        print("Saved successfully to instruments_list.txt")