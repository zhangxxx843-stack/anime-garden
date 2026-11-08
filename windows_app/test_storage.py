import os
import tempfile
import unittest
from pathlib import Path

from windows_app.ledger_domain import LedgerState, LedgerService
from windows_app.ledger_storage import (
    default_data_path,
    deserialize_state,
    load_state,
    save_state,
    serialize_state,
)


class LedgerStorageTests(unittest.TestCase):
    def test_tsv_round_trip_preserves_escaped_text_and_order(self):
        state = LedgerState()
        service = LedgerService(state, clock=lambda: "2026-11-08T10:00:00+08:00")
        service.seed_defaults()
        food = state.categories[0]
        service.add_category("早餐\t小吃", food.id)
        service.add_expense("18.20", food.id, "2026-11-08", "一行\n两列\\备注")
        service.set_budget("2026-11", "100")

        raw = serialize_state(state)
        restored = deserialize_state(raw)

        self.assertEqual(restored, state)
        self.assertIn("早餐\\t小吃", raw)
        self.assertIn("一行\\n两列\\\\备注", raw)

    def test_malformed_records_are_rejected(self):
        malformed = [
            "schemaVersion\t2\n",
            "schemaVersion\t1\nX\tbad\n",
            "schemaVersion\t1\nC\ta\tb\n",
            "schemaVersion\t1\nE\te\tnope\tc\t2026-11-08\t\ta\tb\n",
            "schemaVersion\t1\nB\t2026-13\t100\tnow\n",
        ]
        for raw in malformed:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    deserialize_state(raw)

    def test_missing_file_loads_empty_state_with_default_categories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state = load_state(Path(temp_dir) / "missing.tsv")
        self.assertEqual([category.name for category in state.categories], ["餐饮", "交通", "购物", "学习"])
        self.assertEqual(state.expenses, [])

    def test_save_load_uses_atomic_replacement_and_creates_parent(self):
        state = LedgerState()
        LedgerService(state, clock=lambda: "2026-11-08T10:00:00+08:00").seed_defaults()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "ledger.tsv"
            save_state(path, state)
            self.assertTrue(path.exists())
            self.assertEqual(load_state(path), state)

    def test_default_data_path_honors_test_override(self):
        old_value = os.environ.get("MINIPROJECT_DATA_DIR")
        try:
            os.environ["MINIPROJECT_DATA_DIR"] = "/tmp/suishouji-test-data"
            self.assertEqual(default_data_path(), Path("/tmp/suishouji-test-data/ledger.tsv"))
            os.environ["MINIPROJECT_DATA_DIR"] = "/tmp/custom-ledger.tsv"
            self.assertEqual(default_data_path(), Path("/tmp/custom-ledger.tsv"))
        finally:
            if old_value is None:
                os.environ.pop("MINIPROJECT_DATA_DIR", None)
            else:
                os.environ["MINIPROJECT_DATA_DIR"] = old_value


if __name__ == "__main__":
    unittest.main()
