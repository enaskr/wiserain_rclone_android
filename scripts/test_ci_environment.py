"""Fail CI if a workflow is moved to an external/self-hosted build agent.

These workflows use simple literal runs-on values. Runtime checks provide
a second, independent line of defense.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_LABEL = "ubuntu-24.04"
GUARD_STEP = "- name: Require GitHub-hosted Ubuntu runner"


class HostedOnlyWorkflows(unittest.TestCase):
    def test_every_job_uses_github_hosted_runner(self):
        files = sorted(WORKFLOWS.glob("*.yml"))
        self.assertEqual(
            {file.name for file in files},
            {"build-aar.yml", "translate-readme.yml"},
            "Review newly added workflows and update this allowlist",
        )
        for file in files:
            with self.subTest(workflow=file.name):
                source = file.read_text(encoding="utf-8")
                labels = re.findall(r"^    runs-on:\s*([^\s#]+)", source, re.M)
                self.assertTrue(labels, "No runner labels found")
                self.assertEqual(
                    labels, [EXPECTED_LABEL] * len(labels),
                    "A workflow job switched from the GitHub-hosted runner",
                )
                self.assertEqual(
                    source.count(GUARD_STEP), len(labels),
                    "Every job must check RUNNER_ENVIRONMENT",
                )
                self.assertNotIn("self-hosted", source)
                self.assertNotIn("runs-on: $" + "{{", source)

    def test_no_remote_build_actions_in_workflows(self):
        forbidden = [
            re.compile(r"\b(?:ssh|scp|rsync)\s+(?:-\w+\s+)*\S+@", re.I),
            re.compile(r"\b(?:appleboy/ssh-action|appleboy/scp-action)@", re.I),
        ]
        for file in WORKFLOWS.glob("*.yml"):
            source = file.read_text(encoding="utf-8")
            for regex in forbidden:
                self.assertIsNone(regex.search(source), file.name)

    def test_existing_twice_daily_schedule_unchanged(self):
        source = (WORKFLOWS / "build-aar.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '4 19 * * *'", source)
        self.assertIn("cron: '12 3 * * *'", source)

    def test_release_artifact_has_runner_provenance_gate(self):
        script = (ROOT / "scripts" / "build-aar.sh").read_text(encoding="utf-8")
        workflow = (WORKFLOWS / "build-aar.yml").read_text(encoding="utf-8")
        self.assertIn("runner_environment=github-hosted", workflow)
        self.assertIn("runner_environment=%s", script)
        self.assertIn("RUNNER_ENVIRONMENT", script)


if __name__ == "__main__":
    unittest.main()
