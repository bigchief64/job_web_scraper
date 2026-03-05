# Location Eligibility Tightening

Metadata:
- plan_name: location-eligibility-tightening
- branch_name: location-eligibility-tightening
- status: completed
- owner: codex
- validation_defaults:
  - python -c "import py_compile, pathlib; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('job_hunter').glob('*.py')]; py_compile.compile('main.py', doraise=True)"
  - python main.py --dry-run --limit 5
- rollback_notes: Revert the single build commit and restore prior location-filter behavior from git history.

## Phase 1: Define Location Eligibility Contract
Status: completed
Goal: Establish an unambiguous acceptance contract for location eligibility.
Scope: Define exactly what counts as eligible: confirmed remote only, or New Orleans region hybrid/local; define what is rejected (unknown remote status outside region, non-remote non-region jobs).
Validation:
- Document acceptance matrix in code comments and/or constants in `job_hunter/filters.py`.
- python -c "from job_hunter.filters import classify_remote; print('ok')"
Notes: Include explicit New Orleans aliases (e.g., New Orleans, Metairie, Kenner, Jefferson Parish).
Exit Criteria:
- “Confirmed remote” is explicitly defined as detected labels `remote`, `remote-friendly`, or `remote-us`.
- New Orleans region matching list is explicit and centralized in constants.
- Policy explicitly rejects unknown-remote jobs unless location text matches New Orleans region.

## Phase 2: Implement Filter Logic Changes
Status: completed
Goal: Enforce strict location gating during relevance filtering.
Scope: Update `job_hunter/filters.py` to require either confirmed remote (`True`) or explicit New Orleans-region local/hybrid matches; reject unknown-remote jobs unless they explicitly match New Orleans-region local/hybrid criteria.
Validation:
- python -c "import py_compile, pathlib; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('job_hunter').glob('*.py')]; py_compile.compile('main.py', doraise=True)"
- python -c "from job_hunter.models import Job; from job_hunter.filters import is_relevant_job; print(is_relevant_job(Job('Backend Engineer','Acme','Remote US',True,'backend python aws','https://x','yc')))"
- python -c "from job_hunter.models import Job; from job_hunter.filters import is_relevant_job; print(is_relevant_job(Job('Backend Engineer','Acme','San Francisco, CA',None,'backend python aws hybrid','https://y','yc')))"
Notes: Preserve existing backend-signal precision requirements.
Exit Criteria:
- Confirmed remote backend jobs pass.
- Non-remote and non-region jobs fail.
- Unknown-remote jobs outside New Orleans region fail.

## Phase 3: Add Deterministic Policy Tests
Status: completed
Goal: Prevent regressions in location eligibility rules.
Scope: Add lightweight test module (or deterministic script checks) covering: confirmed remote pass, New Orleans local/hybrid pass, unknown remote outside region fail, known onsite outside region fail.
Validation:
- python -c "import py_compile, pathlib; [py_compile.compile(str(p), doraise=True) for p in pathlib.Path('job_hunter').glob('*.py')]; py_compile.compile('main.py', doraise=True)"
- python -m pytest -q (if pytest exists)
- fallback: python -c "<deterministic assertions script>"
Notes: Use deterministic fixtures; avoid network dependency.
Exit Criteria:
- At least four deterministic policy assertions exist and pass.
- Test coverage includes both allowed and rejected location classes.

## Phase 4: CLI Behavior Verification And Documentation
Status: completed
Goal: Ensure runtime output aligns with new eligibility policy and operational expectations.
Scope: Verify dry-run results reflect stricter policy; update README notes to state only confirmed remote or New Orleans-region local/hybrid roles are returned.
Validation:
- python main.py --dry-run --limit 10
- python main.py --dry-run --limit 10 --db-path temp_validation.db
Notes: Keep existing scoring/output format unchanged.
Exit Criteria:
- README clearly states location policy.
- Dry-run outputs contain only confirmed remote or New Orleans-region local/hybrid eligible roles.

## Risk And Dependency Notes
Status: completed
Goal: Make sequencing and regression risks explicit.
Scope: Ensure filter policy update occurs before tests/docs; capture risk that stricter eligibility may return fewer than 10 results.
Validation:
- Manual checklist review in plan execution notes.
Notes: Fewer results is acceptable and preferred over false positives per precision requirement.
