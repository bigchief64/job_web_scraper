import requests

def fetch_greenhouse(company):

    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except:
        return []

    jobs = []

    for j in data.get("jobs", []):

        jobs.append({
            "title": j["title"],
            "url": j["absolute_url"],
            "company": company
        })

    return jobs