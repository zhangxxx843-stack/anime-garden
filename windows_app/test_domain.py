import unittest

from windows_app.ledger_domain import (
    LedgerService,
    LedgerState,
    Category,
    Expense,
    MonthlyBudget,
    expense_display_text,
)


class LedgerDomainTests(unittest.TestCase):
    def setUp(self):
        self.state = LedgerState()
        self.service = LedgerService(self.state, clock=lambda: "2026-11-08T10:00:00+08:00")
        self.service.seed_defaults()
        self.food = next(category for category in self.state.categories if category.name == "餐饮")

    def test_seed_defaults_creates_empty_default_categories(self):
        self.assertEqual([category.name for category in self.state.categories], ["餐饮", "交通", "购物", "学习"])
        self.assertEqual(self.state.expenses, [])
        self.assertEqual(self.state.budgets, [])

    def test_add_expense_accepts_exact_cents_and_summarizes_by_date(self):
        self.service.add_expense("18.20", self.food.id, "2026-11-08", "午餐")
        self.service.add_expense("1", self.food.id, "2026-11-08")

        summary = self.service.summarize_date("2026-11-08")
        self.assertEqual(summary["total_cents"], 1920)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["by_category"], {self.food.id: 1920})

    def test_invalid_amount_and_date_are_rejected(self):
        for amount in ("", "0", "-1", "12.345", "abc"):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    self.service.add_expense(amount, self.food.id, "2026-11-08")
        with self.assertRaises(ValueError):
            self.service.add_expense("1.20", self.food.id, "2026-02-30")

    def test_duplicate_sibling_category_is_rejected_but_child_name_can_repeat(self):
        with self.assertRaises(ValueError):
            self.service.add_category("餐饮")
        child = self.service.add_category("早餐", self.food.id)
        self.assertEqual(child.parent_id, self.food.id)
        self.service.add_category("早餐", "category-transport")

    def test_budget_status_reports_overrun(self):
        self.service.add_expense("100.00", self.food.id, "2026-11-08")
        budget = self.service.set_budget("2026-11", "80")

        self.assertEqual(budget.amount_cents, 8000)
        self.assertEqual(self.service.budget_status("2026-11"), {
            "month": "2026-11",
            "budget_cents": 8000,
            "spent_cents": 10000,
            "remaining_cents": -2000,
            "over_budget": True,
        })

    def test_update_delete_and_month_summary(self):
        expense = self.service.add_expense("18", self.food.id, "2026-11-08", "午餐")
        self.service.update_expense(expense.id, "22.50", self.food.id, "2026-11-09", "晚餐")
        self.assertEqual(self.service.summarize_month("2026-11")["total_cents"], 2250)
        self.service.delete_expense(expense.id)
        self.assertEqual(self.service.summarize_month("2026-11")["total_cents"], 0)

    def test_note_display_uses_note_only_when_filled(self):
        self.assertEqual(expense_display_text("", "餐饮"), "餐饮")
        self.assertEqual(expense_display_text("  ", "餐饮"), "餐饮")
        self.assertEqual(expense_display_text("午餐 · 食堂", "餐饮"), "午餐 · 食堂")


if __name__ == "__main__":
    unittest.main()
