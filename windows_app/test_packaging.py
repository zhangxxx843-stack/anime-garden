import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingSmokeTests(unittest.TestCase):
    def test_windows_spec_declares_entrypoint_application_and_dist_name(self):
        spec = (ROOT / "packaging" / "windows.spec").read_text(encoding="utf-8")
        self.assertIn("windows_app/main.py", spec)
        self.assertIn("name='Suishouji'", spec)
        self.assertIn("dist/Suishouji", spec)

    def test_workflow_builds_and_uploads_windows_zip(self):
        workflow = (ROOT / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("windows-latest", workflow)
        self.assertIn("python -m unittest", workflow)
        self.assertIn("suishouji-windows-x64.zip", workflow)


if __name__ == "__main__":
    unittest.main()
