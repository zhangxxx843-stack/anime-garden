"""Schema-versioned TSV persistence for the Windows ledger."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .ledger_domain import (
    Category,
    Expense,
    LedgerService,
    LedgerState,
    MonthlyBudget,
    is_valid_date,
    is_valid_month,
)


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _unescape(value: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            result.append(char)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise ValueError("invalid escape sequence")
        escaped = value[index]
        result.append({"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}.get(escaped, "\\" + escaped))
        index += 1
    return "".join(result)


def serialize_state(state: LedgerState) -> str:
    if state.schema_version != 1:
        raise ValueError("unsupported schema version")
    lines = ["schemaVersion\t1"]
    for category in state.categories:
        lines.append(
            "\t".join(
                [
                    "C",
                    _escape(category.id),
                    _escape(category.name),
                    _escape(category.parent_id or ""),
                    _escape(category.created_at),
                    _escape(category.updated_at),
                ]
            )
        )
    for expense in state.expenses:
        lines.append(
            "\t".join(
                [
                    "E",
                    _escape(expense.id),
                    str(expense.amount_cents),
                    _escape(expense.category_id),
                    _escape(expense.date),
                    _escape(expense.note),
                    _escape(expense.created_at),
                    _escape(expense.updated_at),
                ]
            )
        )
    for budget in state.budgets:
        lines.append("\t".join(["B", _escape(budget.month), str(budget.amount_cents), _escape(budget.updated_at)]))
    return "\n".join(lines) + "\n"


def _parse_positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"invalid {label}") from None
    if parsed <= 0:
        raise ValueError(f"invalid {label}")
    return parsed


def deserialize_state(raw: str) -> LedgerState:
    lines = raw.splitlines()
    if not lines or lines[0].lstrip("\ufeff") != "schemaVersion\t1":
        raise ValueError("unsupported or missing schema version")
    state = LedgerState(schema_version=1)
    all_ids: set[str] = set()
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split("\t")
        kind = fields[0]
        if kind == "C":
            if len(fields) != 6:
                raise ValueError("malformed category record")
            category_id, name, parent_id, created_at, updated_at = (_unescape(value) for value in fields[1:])
            if not category_id or not name or category_id in all_ids:
                raise ValueError("invalid category record")
            if parent_id and parent_id not in all_ids:
                raise ValueError("category parent not found")
            state.categories.append(Category(category_id, name, parent_id or None, created_at, updated_at))
            all_ids.add(category_id)
        elif kind == "E":
            if len(fields) != 8:
                raise ValueError("malformed expense record")
            expense_id, amount, category_id, date, note, created_at, updated_at = (
                _unescape(value) for value in fields[1:]
            )
            amount_cents = _parse_positive_int(amount, "expense amount")
            if not expense_id or expense_id in all_ids or category_id not in all_ids or not is_valid_date(date):
                raise ValueError("invalid expense record")
            state.expenses.append(Expense(expense_id, amount_cents, category_id, date, note, created_at, updated_at))
            all_ids.add(expense_id)
        elif kind == "B":
            if len(fields) != 4:
                raise ValueError("malformed budget record")
            month, amount, updated_at = (_unescape(value) for value in fields[1:])
            amount_cents = _parse_positive_int(amount, "budget amount")
            if not is_valid_month(month) or any(item.month == month for item in state.budgets):
                raise ValueError("invalid budget record")
            state.budgets.append(MonthlyBudget(month, amount_cents, updated_at))
        else:
            raise ValueError("unknown record type")
    return state


def default_data_path() -> Path:
    override = os.environ.get("MINIPROJECT_DATA_DIR")
    if override:
        path = Path(override).expanduser()
        return path if path.suffix.lower() == ".tsv" else path / "ledger.tsv"
    if os.name == "nt":
        app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return app_data / "Suishouji" / "ledger.tsv"
    return Path(__file__).resolve().parents[1] / "data" / "ledger.tsv"


def load_state(path: str | Path) -> LedgerState:
    target = Path(path)
    if not target.exists():
        state = LedgerState()
        LedgerService(state).seed_defaults()
        return state
    return deserialize_state(target.read_text(encoding="utf-8"))


def save_state(path: str | Path, state: LedgerState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialize_state(state))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
