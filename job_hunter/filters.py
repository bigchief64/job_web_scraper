GOOD = [
    "backend",
    "api",
    "node",
    "typescript",
    "go",
    "distributed",
    "microservice",
    "aws",
]

BAD = [
    "react",
    "frontend",
    "designer",
    "mobile",
    "ios",
]


def relevant(text):

    text = text.lower()

    for bad in BAD:
        if bad in text:
            return False

    for good in GOOD:
        if good in text:
            return True

    return False


def remote(text):

    text = text.lower()

    if "remote" in text:
        return True

    if "anywhere" in text:
        return True

    if "us" in text and "remote" in text:
        return True

    return False