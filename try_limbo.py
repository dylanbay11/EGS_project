import sys
sys.path.append('epicstore_api')
from epicstore_api import EpicGamesStoreAPI
import logging

api = EpicGamesStoreAPI()
res = api._session.post(
    api._graphql_url,
    json={'query': 'query {}', 'variables': {'locale': 'en-US', 'country': 'US'}}
)
print("STATUS CODE:", res.status_code)
print("RESPONSE TEXT:", res.text)
