import requests
import datetime
import os

url = 'https://docs.google.com/spreadsheets/d/1B2S4kj4PY_U7W5daQyLbv1XvFIFm64o0lFv0Q4fxZIA/export?format=csv'
response = requests.get(url)

if response.status_code == 200:
    today = datetime.date.today().isoformat()
    filepath = f"data/{today}-gsheets.csv"

    with open(filepath, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded successfully to {filepath}")
else:
    print(f"Failed to download: {response.status_code}")
