import unittest

from job_hunter.filters import is_relevant_job
from job_hunter.models import Job


class LocationEligibilityPolicyTests(unittest.TestCase):
    def make_job(self, *, title: str, location: str, description: str) -> Job:
        return Job(
            title=title,
            company="ExampleCo",
            location=location,
            is_remote=None,
            description=description,
            url="https://example.com/job",
            source="yc",
        )

    def test_confirmed_remote_passes(self) -> None:
        job = self.make_job(
            title="Backend Engineer",
            location="Remote US",
            description="Python backend APIs distributed systems AWS",
        )
        self.assertTrue(is_relevant_job(job))

    def test_new_orleans_local_passes(self) -> None:
        job = self.make_job(
            title="Backend Platform Engineer",
            location="New Orleans, LA",
            description="Onsite role building backend APIs with Python",
        )
        self.assertTrue(is_relevant_job(job))

    def test_new_orleans_hybrid_passes(self) -> None:
        job = self.make_job(
            title="Infrastructure Engineer",
            location="Metairie, LA",
            description="Hybrid schedule, AWS backend platform",
        )
        self.assertTrue(is_relevant_job(job))

    def test_unknown_remote_outside_region_fails(self) -> None:
        job = self.make_job(
            title="Backend Engineer",
            location="San Francisco, CA",
            description="Python backend APIs and microservices",
        )
        self.assertFalse(is_relevant_job(job))

    def test_onsite_outside_region_fails(self) -> None:
        job = self.make_job(
            title="Backend Engineer",
            location="Austin, TX",
            description="Onsite backend APIs and AWS",
        )
        self.assertFalse(is_relevant_job(job))


if __name__ == "__main__":
    unittest.main()
