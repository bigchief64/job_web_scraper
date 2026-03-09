import requests
from bs4 import BeautifulSoup

CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/join",
    "/work-with-us"
]


def scan_company(company_name, yc_url):

    jobs = []

    try:

        r = requests.get(yc_url)
        soup = BeautifulSoup(r.text, "html.parser")

        website = None

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if href.startswith("http") and "ycombinator" not in href:
                website = href
                break

        if not website:
            return jobs

        for path in CAREER_PATHS:

            url = website.rstrip("/") + path

            try:

                r = requests.get(url, timeout=5)

                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                for a in soup.find_all("a", href=True):

                    link = a["href"]

                    if "job" in link or "career" in link:

                        if link.startswith("/"):
                            link = website + link

                        jobs.append({
                            "company": company_name,
                            "url": link,
                            "title": a.text.strip()
                        })

            except:
                pass

    except:
        pass

    return jobs