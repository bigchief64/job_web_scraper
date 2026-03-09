import requests

BASE = "https://hacker-news.firebaseio.com/v0"


def fetch_comments(story):

    jobs = []

    for cid in story.get("kids", []):

        comment = requests.get(f"{BASE}/item/{cid}.json").json()

        if not comment:
            continue

        text = comment.get("text","")

        jobs.append({
            "id": comment["id"],
            "text": text,
            "url": f"https://news.ycombinator.com/item?id={comment['id']}"
        })

    return jobs