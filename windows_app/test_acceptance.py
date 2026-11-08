import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from windows_app.ledger_domain import LedgerService, LedgerState
from windows_app.ledger_storage import serialize_state
from windows_app.main import LedgerWindow


class MemoryStore:
    def __init__(self):
        self.saved = 0

    def save(self, state):
        self.saved += 1


class WindowsAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.state = LedgerState()
        self.service = LedgerService(self.state, clock=lambda: "2026-11-08T10:00:00+08:00")
        self.service.seed_defaults()
        self.store = MemoryStore()
        self.window = LedgerWindow(self.service, self.store)
        self.window.show()
        self.app.processEvents()
        self.food = self.state.categories[0]

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_statistics_page_sums_selected_month(self):
        self.service.add_expense("18", self.food.id, "2026-11-08")
        self.service.add_expense("12", self.food.id, "2026-11-09")
        self.window.show_page("stats")
        self.app.processEvents()
        self.assertEqual(self.window.stats_total_label.text(), "¥30.00")
        self.assertIn("餐饮", self.window.stats_table.item(0, 0).text())

    def test_budget_page_shows_true_overrun_and_caps_progress(self):
        self.service.add_expense("100", self.food.id, "2026-11-08")
        self.window.show_page("budget")
        self.window.budget_amount_edit.setText("80")
        self.window.budget_save_button.click()
        self.app.processEvents()
        self.assertEqual(self.window.budget_progress.value(), 100)
        self.assertIn("超出 ¥20.00", self.window.budget_status_label.text())

    def test_categories_page_adds_and_renames_category_and_picker_refreshes(self):
        self.window.show_page("categories")
        self.window.category_name_edit.setText("早餐")
        self.window.category_parent_combo.setCurrentText("餐饮")
        self.window.category_add_button.click()
        self.app.processEvents()
        self.assertIn("早餐", [self.window.category_list.item(i).text() for i in range(self.window.category_list.count())])
        self.window.category_list.setCurrentRow(self.window.category_list.count() - 1)
        self.window.category_name_edit.setText("早餐外带")
        self.window.category_rename_button.click()
        self.app.processEvents()
        self.assertIn("早餐外带", [self.window.category_list.item(i).text() for i in range(self.window.category_list.count())])
        self.window.open_add_expense()
        self.app.processEvents()
        self.assertTrue(any(button.text() == "餐饮" for button in self.window.category_picker.findChildren(type(self.window.add_button))))

    def test_import_success_replaces_state_and_persists(self):
        external = LedgerState()
        external_service = LedgerService(external, clock=lambda: "2026-11-08T10:00:00+08:00")
        external_service.seed_defaults()
        external_service.add_expense("9.90", external.categories[1].id, "2026-11-08", "公交")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "old.tsv"
            path.write_text(serialize_state(external), encoding="utf-8")
            self.assertTrue(self.window.import_ledger(path))
        self.assertEqual(len(self.state.expenses), 1)
        self.assertEqual(self.state.expenses[0].note, "公交")
        self.assertEqual(self.store.saved, 1)

    def test_import_cancel_and_rejection_preserve_current_data(self):
        self.service.add_expense("5", self.food.id, "2026-11-08", "已有")
        before = list(self.state.expenses)
        self.assertFalse(self.window.import_ledger(""))
        self.assertEqual(self.state.expenses, before)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.tsv"
            path.write_text("schemaVersion\t1\nE\tbroken\tnope\n", encoding="utf-8")
            self.assertFalse(self.window.import_ledger(path))
        self.assertEqual(self.state.expenses, before)
        self.assertEqual(self.store.saved, 0)


if __name__ == "__main__":
    unittest.main()
