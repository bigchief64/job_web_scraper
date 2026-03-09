import requests

BASE = "https://hacker-news.firebaseio.com/v0"


def get_who_is_hiring():

    r = requests.get(f"{BASE}/askstories.json")
    stories = r.json()

    for story_id in stories:

        item = requests.get(f"{BASE}/item/{story_id}.json").json()

        if "who is hiring" in item.get("title","").lower():

            return item

    return None