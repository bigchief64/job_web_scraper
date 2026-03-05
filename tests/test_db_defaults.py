import unittest
from pathlib import Path

from job_hunter.main import DEFAULT_DB_PATH


class DefaultDbPathTests(unittest.TestCase):
    def test_default_db_path_is_not_project_root_file(self) -> None:
        # Prevent stale repo-local DB files from making first runs look empty.
        self.assertEqual(Path(DEFAULT_DB_PATH).name, "jobs_seen.db")
        self.assertIn('.job_hunter', [part.lower() for part in Path(DEFAULT_DB_PATH).parts])
        self.assertNotEqual(Path(DEFAULT_DB_PATH), Path('jobs_seen.db'))


if __name__ == '__main__':
    unittest.main()
