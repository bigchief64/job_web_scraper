import requests


def fetch_lever(company):

    url = f"https://api.lever.co/v0/postings/{company}?mode=json"

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    jobs = []

    for j in data:
        if not isinstance(j, dict):
            continue

        title = j.get("text")
        job_url = j.get("hostedUrl")
        if not title or not job_url:
            continue

        jobs.append({
            "title": title,
            "url": job_url,
            "company": company
        })

    return jobs
