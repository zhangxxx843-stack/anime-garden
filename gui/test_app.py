import unittest

from app import build_command, expense_display_text, parse_snapshot


class GuiProtocolTest(unittest.TestCase):
    def test_builds_backend_command_without_shell(self):
        command = build_command("/tmp/main", ["snapshot"])
        self.assertEqual(command, ["/tmp/main", "snapshot"])

    def test_parses_snapshot_records(self):
        snapshot = """schemaVersion\t1
C\tcategory-food\t餐饮\t\t2026-11-08\t2026-11-08
E\texpense-1\t1800\tcategory-food\t2026-11-08\t午餐\\t食堂\t2026-11-08\t2026-11-08
B\t2026-11\t10000\t2026-11-08
"""
        parsed = parse_snapshot(snapshot)
        self.assertEqual(parsed["categories"][0]["name"], "餐饮")
        self.assertEqual(parsed["expenses"][0]["amount"], 1800)
        self.assertEqual(parsed["budgets"]["2026-11"]["amount"], 10000)

    def test_expense_display_prefers_note_and_falls_back_to_category(self):
        self.assertEqual(expense_display_text("午餐 · 食堂", "餐饮"), "午餐 · 食堂")
        self.assertEqual(expense_display_text("  ", "餐饮"), "餐饮")


if __name__ == "__main__":
    unittest.main()
