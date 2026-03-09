from .hn_fetch import get_who_is_hiring
from .hn_jobs import fetch_comments
from .filters import relevant, remote
from .storage import init_db, seen, mark_seen

LIMIT = 10


def main():

    init_db()

    story = get_who_is_hiring()

    if not story:
        print("Could not find HN hiring thread")
        return

    comments = fetch_comments(story)

    results = []

    for job in comments:

        if seen(job["id"]):
            continue

        text = job["text"]

        if not relevant(text):
            continue

        if not remote(text):
            continue

        results.append(job)

        if len(results) >= LIMIT:
            break

    for job in results:

        print()
        print(job["url"])
        print()
        print(job["text"][:400])
        print()

        mark_seen(job["id"])


if __name__ == "__main__":
    main()