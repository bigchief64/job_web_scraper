# Job Hunter CLI

Local Python CLI for daily backend job discovery from YC Work at a Startup and Wellfound.

## Features

- Scrapes from:
  - YC Work at a Startup (`https://www.workatastartup.com/jobs`)
  - Wellfound (`https://wellfound.com/jobs`)
- Normalizes jobs into a shared dataclass model.
- Filters aggressively for backend-relevant roles using title + description.
- Scores jobs with weighted keyword matching and drops negative-score results.
- Prioritizes remote roles and keeps jobs with unknown remote status marked in output.
- Persists previously returned URLs in SQLite to avoid duplicates across runs.

## Install

```bash
pip install requests beautifulsoup4 playwright
playwright install
```

## Run

```bash
python main.py
```

Optional flags:

- `--limit 10` number of jobs to print.
- `--dry-run` do not mark results as seen.
- `--db-path path/to/jobs_seen.db` custom SQLite location.

## Output Example

```text
Score: 8.7
Title: Backend Engineer
Company: ExampleCo
Location: Remote
Source: YC
URL: https://...
```

## Notes

- Wellfound may block plain HTTP scraping; Playwright is the primary path.
- If a source parser fails, the CLI continues with remaining sources and emits warnings.
- Future boards (for example LinkedIn) can be added as new scraper modules and wired in `job_hunter/pipeline.py`.
