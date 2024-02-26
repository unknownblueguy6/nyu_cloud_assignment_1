import requests
import json
# from dynamodb_json import json_util as json

SEARCH_ENDPOINT = "https://api.yelp.com/v3/businesses/search"
LIMIT = 50

LOCATION = "Manhattan"
MAX_RESTAURANTS = 100

headers = {
    "accept": "application/json",
    "Authorization": "Bearer UcJpFtJM9oPEUpil7Z8Er2LUJk30V4ZOKRc9obSlBE74Kjtj8Uj5HgajT_bDCYTBfLUq5IhaljIp8VcuyAkCZ2B6NwWjbMK6m07v8H7tTR-l-P5dlxsuRLWifezVZXYx"
}

cuisines = ["Italian", "Indian", "Chinese", "Middle Eastern", "Mexican"]
cuisine_categories = ["italian", "indpak", "chinese", "mideastern", "mexican"]

businesses = []
# for i, c in enumerate(cuisine_categories):
#     def addField(x):
#         x["cuisine"] = cuisines[i]
#         return x
#     for j in range(MAX_RESTAURANTS // LIMIT):
#         offset = j*LIMIT
#         search_url = f"{SEARCH_ENDPOINT}?location={LOCATION}&categories={c}&sort_by=best_match&limit={LIMIT}&offset={offset}"
#         response = requests.get(search_url, headers=headers)
#         businesses += list(map(addField, response.json()['businesses']))

# with open('yelp-restaurants.json', 'w') as fp:
#     json.dump(businesses, fp)


with open('yelp-restaurants.json', 'r', encoding='utf-8') as fp:
    businesses = json.load(fp)

with open('index.json', 'w') as fp:
    for i, b in enumerate(businesses):
        doc = {
            "id":b["id"],
            "cuisine":b["cuisine"]
        }
        index = {
            "index": {
                "_index": "restaurant",
                "_id": str(i+1),
            }
        }
        fp.write(f"{json.dumps(index)}\n")
        fp.write(f"{json.dumps(doc)}\n")
    