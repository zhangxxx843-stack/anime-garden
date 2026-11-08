"""Pure Python ledger rules shared by the Windows desktop UI and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Callable, Optional


DEFAULT_CATEGORIES = (
    ("category-food", "餐饮"),
    ("category-transport", "交通"),
    ("category-shopping", "购物"),
    ("category-learning", "学习"),
)


@dataclass(eq=True)
class Category:
    id: str
    name: str
    parent_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(eq=True)
class Expense:
    id: str
    amount_cents: int
    category_id: str
    date: str
    note: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(eq=True)
class MonthlyBudget:
    month: str
    amount_cents: int
    updated_at: str = ""


@dataclass(eq=True)
class LedgerState:
    categories: list[Category] = field(default_factory=list)
    expenses: list[Expense] = field(default_factory=list)
    budgets: list[MonthlyBudget] = field(default_factory=list)
    schema_version: int = 1


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return len(value) == 10
    except (TypeError, ValueError):
        return False


def is_valid_month(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m")
        return len(value) == 7
    except (TypeError, ValueError):
        return False


def parse_amount_cents(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("amount must be positive and have at most two decimals")
    if isinstance(value, int):
        cents = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("amount is required")
        try:
            decimal = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValueError("amount must be a number") from None
        if not decimal.is_finite() or decimal <= 0:
            raise ValueError("amount must be positive")
        rounded = decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded != decimal:
            raise ValueError("amount must have at most two decimals")
        cents = int(rounded * 100)
    if cents <= 0:
        raise ValueError("amount must be positive")
    return cents


def expense_display_text(note: str, category_name: str) -> str:
    cleaned_note = (note or "").strip()
    return cleaned_note if cleaned_note else category_name


class LedgerService:
    def __init__(self, state: LedgerState | None = None, clock: Callable[[], str] | None = None):
        self.state = state if state is not None else LedgerState()
        self._clock = clock or _now_iso

    def _timestamp(self, explicit: str | None) -> str:
        return explicit or self._clock()

    def _next_id(self, prefix: str, existing: list[str]) -> str:
        index = 1
        existing_set = set(existing)
        while f"{prefix}-{index}" in existing_set:
            index += 1
        return f"{prefix}-{index}"

    def _category(self, category_id: str) -> Category:
        for category in self.state.categories:
            if category.id == category_id:
                return category
        raise ValueError("category not found")

    def _expense(self, expense_id: str) -> Expense:
        for expense in self.state.expenses:
            if expense.id == expense_id:
                return expense
        raise ValueError("expense not found")

    def _validate_category_name(self, name: str, parent_id: str | None, current_id: str | None = None) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("category name is required")
        if len(cleaned) > 40:
            raise ValueError("category name is too long")
        if parent_id is not None:
            self._category(parent_id)
        duplicate = any(
            category.id != current_id
            and category.parent_id == parent_id
            and category.name.casefold() == cleaned.casefold()
            for category in self.state.categories
        )
        if duplicate:
            raise ValueError("duplicate category")
        return cleaned

    def seed_defaults(self, now: str | None = None) -> list[Category]:
        timestamp = self._timestamp(now)
        added: list[Category] = []
        for category_id, name in DEFAULT_CATEGORIES:
            if any(category.id == category_id for category in self.state.categories):
                continue
            category = Category(category_id, name, None, timestamp, timestamp)
            self.state.categories.append(category)
            added.append(category)
        return added

    def add_category(self, name: str, parent_id: str | None = None, now: str | None = None) -> Category:
        cleaned = self._validate_category_name(name, parent_id)
        timestamp = self._timestamp(now)
        category = Category(
            self._next_id("category", [item.id for item in self.state.categories]),
            cleaned,
            parent_id,
            timestamp,
            timestamp,
        )
        self.state.categories.append(category)
        return category

    def rename_category(self, category_id: str, name: str, now: str | None = None) -> Category:
        category = self._category(category_id)
        category.name = self._validate_category_name(name, category.parent_id, category.id)
        category.updated_at = self._timestamp(now)
        return category

    def add_expense(
        self,
        amount: object,
        category_id: str,
        date: str,
        note: str = "",
        now: str | None = None,
    ) -> Expense:
        amount_cents = parse_amount_cents(amount)
        self._category(category_id)
        if not is_valid_date(date):
            raise ValueError("invalid date")
        timestamp = self._timestamp(now)
        expense = Expense(
            self._next_id("expense", [item.id for item in self.state.expenses]),
            amount_cents,
            category_id,
            date,
            (note or "").strip(),
            timestamp,
            timestamp,
        )
        self.state.expenses.append(expense)
        return expense

    def update_expense(
        self,
        expense_id: str,
        amount: object,
        category_id: str,
        date: str,
        note: str = "",
        now: str | None = None,
    ) -> Expense:
        expense = self._expense(expense_id)
        amount_cents = parse_amount_cents(amount)
        self._category(category_id)
        if not is_valid_date(date):
            raise ValueError("invalid date")
        expense.amount_cents = amount_cents
        expense.category_id = category_id
        expense.date = date
        expense.note = (note or "").strip()
        expense.updated_at = self._timestamp(now)
        return expense

    def delete_expense(self, expense_id: str) -> None:
        self._expense(expense_id)
        self.state.expenses[:] = [expense for expense in self.state.expenses if expense.id != expense_id]

    def set_budget(self, month: str, amount: object, now: str | None = None) -> MonthlyBudget:
        if not is_valid_month(month):
            raise ValueError("invalid month")
        amount_cents = parse_amount_cents(amount)
        timestamp = self._timestamp(now)
        for budget in self.state.budgets:
            if budget.month == month:
                budget.amount_cents = amount_cents
                budget.updated_at = timestamp
                return budget
        budget = MonthlyBudget(month, amount_cents, timestamp)
        self.state.budgets.append(budget)
        return budget

    def summarize_date(self, date: str) -> dict:
        if not is_valid_date(date):
            raise ValueError("invalid date")
        matching = [expense for expense in self.state.expenses if expense.date == date]
        by_category: dict[str, int] = {}
        for expense in matching:
            by_category[expense.category_id] = by_category.get(expense.category_id, 0) + expense.amount_cents
        return {"date": date, "count": len(matching), "total_cents": sum(by_category.values()), "by_category": by_category}

    def summarize_month(self, month: str) -> dict:
        if not is_valid_month(month):
            raise ValueError("invalid month")
        matching = [expense for expense in self.state.expenses if expense.date.startswith(f"{month}-")]
        by_category: dict[str, int] = {}
        for expense in matching:
            by_category[expense.category_id] = by_category.get(expense.category_id, 0) + expense.amount_cents
        return {"month": month, "count": len(matching), "total_cents": sum(by_category.values()), "by_category": by_category}

    def budget_status(self, month: str) -> dict:
        if not is_valid_month(month):
            raise ValueError("invalid month")
        budget = next((item for item in self.state.budgets if item.month == month), None)
        budget_cents = budget.amount_cents if budget else 0
        spent_cents = self.summarize_month(month)["total_cents"]
        remaining_cents = budget_cents - spent_cents
        return {
            "month": month,
            "budget_cents": budget_cents,
            "spent_cents": spent_cents,
            "remaining_cents": remaining_cents,
            "over_budget": bool(budget and spent_cents > budget_cents),
        }
