import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from windows_app.ledger_domain import LedgerService, LedgerState
from windows_app.main import LedgerWindow


class MemoryStore:
    def __init__(self):
        self.saved = 0
        self.fail = False

    def save(self, state):
        if self.fail:
            raise OSError("disk is unavailable")
        self.saved += 1


class LedgerWindowTests(unittest.TestCase):
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

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_window_constructs_with_four_navigation_actions_and_empty_state(self):
        self.assertEqual(self.window.current_page_key, "details")
        self.assertEqual(len(self.window.navigation_buttons), 4)
        self.assertTrue(self.window.empty_label.isVisible())
        for key in ("stats", "budget", "categories", "details"):
            self.window.navigation_buttons[key].click()
            self.app.processEvents()
            self.assertEqual(self.window.current_page_key, key)

    def test_central_add_action_opens_category_picker(self):
        self.window.add_button.click()
        self.app.processEvents()
        self.assertIsNotNone(self.window.category_picker)
        self.assertTrue(self.window.category_picker.isVisible())

    def test_note_display_prefers_note_and_falls_back_to_category(self):
        food = self.state.categories[0]
        self.service.add_expense("18.20", food.id, "2026-11-08", "午餐 · 食堂")
        self.service.add_expense("3", food.id, "2026-11-08")
        self.window.refresh_details()
        self.app.processEvents()
        row_text = [
            self.window.expense_table.item(row, 3).text()
            for row in range(self.window.expense_table.rowCount())
        ]
        self.assertCountEqual(row_text, ["午餐 · 食堂", "餐饮"])

    def test_failed_save_keeps_expense_dialog_open(self):
        food = self.state.categories[0]
        self.store.fail = True
        self.window.open_expense_dialog(food.id)
        dialog = self.window.expense_dialog
        dialog.amount_edit.setText("18.00")
        dialog.save_button.click()
        self.app.processEvents()
        self.assertTrue(dialog.isVisible())
        self.assertIn("保存失败", dialog.error_label.text())
        self.assertEqual(self.state.expenses, [])


if __name__ == "__main__":
    unittest.main()
