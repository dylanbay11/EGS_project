import requests
import json

print("\nTesting tag query...")
try:
    url2 = "https://store-content.ak.epicgames.com/api/en-US/content/products/limbo"
    response2 = requests.get(url2)
    data = response2.json()
    print("KEYS:", data.keys())
    if "pages" in data:
        print("Pages info:", len(data["pages"]))
        page = data["pages"][0]
        print("Page keys:", page.keys())
        if "data" in page:
             print("Data inside page keys:", page["data"].keys())
             if "about" in page["data"]:
                 print("About keys:", page["data"]["about"].keys())

except Exception as e:
    print(e)
