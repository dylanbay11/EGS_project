import requests

url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"

print("Testing free games...")
try:
    response = requests.get(url)
    print("Status:", response.status_code)
    print("First 100 chars:", response.text[:100])
except Exception as e:
    print(e)
