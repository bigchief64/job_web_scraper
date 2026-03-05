# Backend Job Discovery CLI

Metadata:
- plan_name: backend-job-discovery-cli
- branch_name: backend-job-discovery-cli
- status: completed
- owner: codex
- validation_defaults:
  - python -m py_compile job_hunter/*.py main.py
  - python main.py --help
- rollback_notes: Revert the single build commit (`git revert <commit>`), remove generated SQLite/cache artifacts, and delete branch `backend-job-discovery-cli` if abandonment is required.

## Phase 1: Project Skeleton, Models, And CLI Contract
Status: completed
Goal: Establish a modular CLI codebase with shared job model and deterministic command surface.
Scope: Create package layout (`job_hunter/`) with `models.py`, `storage.py`, `filters.py`, `scoring.py`, `yc_scraper.py`, `wellfound_scraper.py`, orchestration module, and top-level `main.py` entrypoint with args (`--limit`, `--dry-run`, `--db-path`).
Validation:
- python -m py_compile job_hunter/*.py main.py
- python main.py --help
- python main.py --dry-run --limit 1
Notes: This phase only wires interfaces and stubs; no production scraping logic beyond safe placeholders.
Exit Criteria:
- `Job` dataclass exists with required fields (title, company, location, remote flag, description, url, source).
- CLI executes without tracebacks and exposes required options.

## Phase 2: SQLite Storage And Seen-URL Deduplication
Status: completed
Goal: Persist previously returned URLs and suppress duplicates across runs.
Scope: Implement `init_db()`, `job_seen(url)`, and `mark_job_seen(url)` with schema `jobs_seen(url TEXT PRIMARY KEY, first_seen TIMESTAMP)`; call storage initialization at startup; dedupe before final selection.
Validation:
- python -m py_compile job_hunter/*.py main.py
- python -c "from job_hunter.storage import init_db, mark_job_seen, job_seen; init_db(); mark_job_seen('https://example.com/a'); print(job_seen('https://example.com/a'))"
- python -c "from job_hunter.storage import init_db, mark_job_seen; init_db(); mark_job_seen('https://example.com/a'); mark_job_seen('https://example.com/a'); print('ok')"
Notes: Use idempotent inserts (`INSERT OR IGNORE`) to prevent duplicate-write exceptions.
Exit Criteria:
- Repeat runs never re-emit URLs already marked seen.
- DB file is created automatically if missing.

## Phase 3: Precision Filters And Weighted Scoring
Status: completed
Goal: Implement aggressive backend-role filtering and deterministic relevance ranking.
Scope: Build case-insensitive title+description keyword evaluation; include positive/negative tech signals; enforce remote preference (remote/remote-friendly/remote US) while retaining uncertain remote jobs marked as unknown; discard negative-score jobs; sort descending by score.
Validation:
- python -m py_compile job_hunter/*.py main.py
- python -c "from job_hunter.models import Job; from job_hunter.scoring import score_job; j=Job('Backend Engineer','Acme','Remote',True,'Node TypeScript APIs AWS distributed systems','https://x','yc'); print(score_job(j))"
- python -c "from job_hunter.models import Job; from job_hunter.filters import is_relevant_job; j=Job('Frontend React Engineer','Acme','Remote',True,'UI React', 'https://x2','wellfound'); print(is_relevant_job(j))"
Notes: Precision over recall is mandatory; false positives are treated as defects.
Exit Criteria:
- Roles dominated by frontend/mobile/design/product terms are excluded.
- Backend-heavy jobs receive reproducible numeric scores aligned with required weights.

## Phase 4: Source Scrapers (YC + Wellfound) With Fallback Strategy
Status: completed
Goal: Extract normalized jobs from both sources using robust selectors and error-tolerant parsing.
Scope: Implement independent scraper modules; Playwright headless primary path with wait strategy, and requests+BeautifulSoup fallback if browser flow fails; extract required fields; paginate when discoverable.
Validation:
- python -m py_compile job_hunter/*.py main.py
- python main.py --dry-run --limit 5
- python -c "from job_hunter.yc_scraper import scrape_yc_jobs; from job_hunter.wellfound_scraper import scrape_wellfound_jobs; print('yc_ok', isinstance(scrape_yc_jobs(), list)); print('wf_ok', isinstance(scrape_wellfound_jobs(), list))"
Notes: Avoid brittle nth-child selectors; prefer semantic/text-based anchors and resilient null handling.
Exit Criteria:
- Both sources return normalized `Job` objects (possibly empty list on transient source failure, without crashing CLI).
- Scraper failures are surfaced as warnings and do not abort entire run.

## Phase 5: End-to-End Pipeline, Output Contract, And Runbook
Status: completed
Goal: Ship a daily-runnable CLI that returns up to 10 fresh backend-role links in required terminal format.
Scope: Finalize full pipeline (`scrape -> normalize -> filter -> score -> dedupe -> sort -> top N -> print -> mark seen`), render exact output blocks, add dependency/setup instructions including `playwright install`, and document operational caveats.
Validation:
- python -m py_compile job_hunter/*.py main.py
- python main.py --limit 10
- python main.py --limit 10
- python main.py --dry-run --limit 3
Notes: Keep extension seam for future LinkedIn module but do not implement LinkedIn scraping.
Exit Criteria:
- Terminal output includes Score, Title, Company, Location, Source, URL per result.
- Second non-dry run avoids returning first-run URLs due to seen tracking.
- README/run instructions are sufficient for fresh environment setup.

## Risk And Test Coverage Notes
Status: completed
Goal: Make validation expectations explicit for network-dependent scraping behavior.
Scope: Add fixture-free smoke checks plus deterministic unit-style checks for storage/filter/scoring paths; document that live scraping may vary by source availability/anti-bot changes.
Validation:
- python -m py_compile job_hunter/*.py main.py
- python main.py --dry-run --limit 2
Notes: If source markup changes, adjust parser selectors without changing filtering/scoring contracts.
