import requests

url = "https://store.epicgames.com/graphql"
headers = {'content-type': 'application/json;charset=UTF-8'}
payload = {
    "query": "query searchStoreQuery($keywords: String, $country: String!, $locale: String) { Catalog { searchStore(keywords: $keywords, country: $country, locale: $locale) { elements { title id } } } }",
    "variables": {"keywords": "Limbo", "country": "US", "locale": "en-US"}
}

print("Testing direct GraphQL request...")
try:
    response = requests.post(url, headers=headers, json=payload)
    print("Status:", response.status_code)
    print("Response text length:", len(response.text))
    if response.status_code != 200:
        print("Is it Cloudflare?", "cloudflare" in response.text.lower())
except Exception as e:
    print(e)

print("\nTesting store content api (get_product)...")
try:
    url2 = "https://store-content.ak.epicgames.com/api/en-US/content/products/limbo"
    response2 = requests.get(url2)
    print("Status:", response2.status_code)
    print("Response length:", len(response2.text))
    if response2.status_code == 200:
        print("First 100 chars:", response2.text[:100])
except Exception as e:
    print(e)
