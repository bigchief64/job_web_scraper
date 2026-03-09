import requests
from bs4 import BeautifulSoup

URL = "https://www.ycombinator.com/companies"


def get_companies():

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    companies = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if href.startswith("/companies/"):

            name = a.text.strip()
            url = "https://www.ycombinator.com" + href

            companies.append((name, url))

    return companies