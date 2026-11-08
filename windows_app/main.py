"""PySide6 Windows desktop client for the offline ledger."""

from __future__ import annotations

import sys
from copy import deepcopy
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QDateEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ledger_domain import LedgerService, LedgerState, expense_display_text
from .ledger_storage import default_data_path, load_state, save_state


def money(cents: int) -> str:
    return f"¥{cents / 100:,.2f}"


class FileStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, state: LedgerState) -> None:
        save_state(self.path, state)


class CategoryPicker(QDialog):
    category_chosen = Signal(str)

    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择大类")
        self.setModal(False)
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        title = QLabel("这笔支出属于哪个大类？")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        for category in categories:
            button = QPushButton(category.name)
            button.setObjectName("categoryChoice")
            button.clicked.connect(lambda _checked=False, category_id=category.id: self._choose(category_id))
            layout.addWidget(button)

    def _choose(self, category_id: str) -> None:
        self.category_chosen.emit(category_id)
        self.close()


class ExpenseDialog(QDialog):
    def __init__(self, category_name: str, expense=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑支出" if expense else "记一笔")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        title = QLabel("编辑支出" if expense else "记一笔")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("例如 18.50")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.category_label = QLabel(category_name)
        self.category_label.setObjectName("dialogValue")
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("可选：午餐、公交、书名……")
        form.addRow("金额", self.amount_edit)
        form.addRow("日期", self.date_edit)
        form.addRow("大类", self.category_label)
        form.addRow("备注", self.note_edit)
        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("primaryButton")
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.close)
        buttons = QDialogButtonBox()
        buttons.addButton(self.save_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        if expense is not None:
            self.amount_edit.setText(f"{expense.amount_cents / 100:.2f}")
            parsed = QDate.fromString(expense.date, "yyyy-MM-dd")
            if parsed.isValid():
                self.date_edit.setDate(parsed)
            self.note_edit.setText(expense.note)


class LedgerWindow(QMainWindow):
    def __init__(self, service: LedgerService, store):
        super().__init__()
        self.service = service
        self.store = store
        self.category_picker = None
        self.expense_dialog = None
        self.current_page_key = "details"
        self.setWindowTitle("随手记 · Windows")
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)
        self._build_shell()
        self.refresh_details()

    def _build_shell(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 28, 24, 24)
        brand = QLabel("随手记")
        brand.setObjectName("brand")
        subtitle = QLabel("离线账本")
        subtitle.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(30)

        self.navigation_buttons = {}
        for key, label in (("details", "明细"), ("stats", "统计"), ("budget", "预算"), ("categories", "分类")):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.clicked.connect(lambda _checked=False, page_key=key: self.show_page(page_key))
            self.navigation_buttons[key] = button
            sidebar_layout.addWidget(button)
        sidebar_layout.addStretch(1)
        self.add_button = QPushButton("＋ 记一笔")
        self.add_button.setObjectName("primaryAddButton")
        self.add_button.clicked.connect(self.open_add_expense)
        sidebar_layout.addWidget(self.add_button)
        root_layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_details_page())
        self.pages.addWidget(self._build_placeholder_page("统计", "按月查看支出趋势与分类占比。"))
        self.pages.addWidget(self._build_placeholder_page("预算", "为每个月设置预算，及时看到剩余金额。"))
        self.pages.addWidget(self._build_placeholder_page("分类", "管理你的大类和小类。"))
        root_layout.addWidget(self.pages, 1)
        self.show_page("details")

    def _build_details_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(18)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("明细")
        title.setObjectName("pageTitle")
        self.details_hint = QLabel("记录今天的每一笔支出")
        self.details_hint.setObjectName("pageHint")
        title_box.addWidget(title)
        title_box.addWidget(self.details_hint)
        header.addLayout(title_box)
        header.addStretch(1)
        self.date_filter = QDateEdit(QDate.currentDate())
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setObjectName("dateFilter")
        self.date_filter.dateChanged.connect(self.refresh_details)
        header.addWidget(QLabel("日期"))
        header.addWidget(self.date_filter)
        layout.addLayout(header)

        cards = QHBoxLayout()
        self.total_card = self._summary_card("今日支出", "¥0.00")
        self.count_card = self._summary_card("记录笔数", "0 笔")
        cards.addWidget(self.total_card)
        cards.addWidget(self.count_card)
        cards.addStretch(1)
        layout.addLayout(cards)

        table_frame = QFrame()
        table_frame.setObjectName("tableFrame")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.empty_label = QLabel("今天还没有记录\n点击左侧“＋ 记一笔”开始记录")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.empty_label)
        self.expense_table = QTableWidget(0, 4)
        self.expense_table.setHorizontalHeaderLabels(["日期", "大类", "金额", "说明"])
        self.expense_table.setObjectName("expenseTable")
        self.expense_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.expense_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.expense_table.verticalHeader().setVisible(False)
        self.expense_table.horizontalHeader().setStretchLastSection(True)
        self.expense_table.setColumnWidth(0, 140)
        self.expense_table.setColumnWidth(1, 160)
        self.expense_table.setColumnWidth(2, 150)
        table_layout.addWidget(self.expense_table)
        layout.addWidget(table_frame, 1)
        return page

    def _summary_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setMinimumWidth(210)
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 16, 20, 16)
        caption = QLabel(label)
        caption.setObjectName("summaryCaption")
        value_label = QLabel(value)
        value_label.setObjectName("summaryValue")
        box.addWidget(caption)
        box.addWidget(value_label)
        card.value_label = value_label
        return card

    def _build_placeholder_page(self, title_text: str, hint: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        note = QLabel(hint)
        note.setObjectName("pageHint")
        layout.addWidget(note)
        panel = QFrame()
        panel.setObjectName("placeholderPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setAlignment(Qt.AlignCenter)
        panel_layout.addWidget(QLabel("这一页正在接入 Windows 版业务数据。"))
        layout.addWidget(panel, 1)
        return page

    def show_page(self, page_key: str) -> None:
        index = {"details": 0, "stats": 1, "budget": 2, "categories": 3}[page_key]
        self.pages.setCurrentIndex(index)
        self.current_page_key = page_key
        for key, button in self.navigation_buttons.items():
            button.setProperty("active", key == page_key)
            button.style().unpolish(button)
            button.style().polish(button)
        if page_key == "details":
            self.refresh_details()

    def refresh_details(self) -> None:
        if not hasattr(self, "expense_table"):
            return
        selected_date = self.date_filter.date().toString("yyyy-MM-dd")
        indexed_expenses = [
            (index, expense)
            for index, expense in enumerate(self.service.state.expenses)
            if expense.date == selected_date
        ]
        indexed_expenses.sort(key=lambda item: (item[1].date, item[1].created_at, item[0]), reverse=True)
        expenses = [expense for _index, expense in indexed_expenses]
        total = sum(expense.amount_cents for expense in expenses)
        self.total_card.value_label.setText(money(total))
        self.count_card.value_label.setText(f"{len(expenses)} 笔")
        self.expense_table.setRowCount(len(expenses))
        for row, expense in enumerate(expenses):
            category = next((item for item in self.service.state.categories if item.id == expense.category_id), None)
            category_name = category.name if category else "未分类"
            values = [expense.date, category_name, money(expense.amount_cents), expense_display_text(expense.note, category_name)]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if column != 2 else Qt.AlignRight | Qt.AlignVCenter)
                self.expense_table.setItem(row, column, item)
        self.empty_label.setVisible(not expenses)
        self.expense_table.setVisible(bool(expenses))

    def open_add_expense(self) -> None:
        categories = [category for category in self.service.state.categories if category.parent_id is None]
        self.category_picker = CategoryPicker(categories, self)
        self.category_picker.category_chosen.connect(self.open_expense_dialog)
        self.category_picker.show()
        self.category_picker.raise_()
        self.category_picker.activateWindow()

    def open_expense_dialog(self, category_id: str, expense=None) -> None:
        category = next(item for item in self.service.state.categories if item.id == category_id)
        self.expense_dialog = ExpenseDialog(category.name, expense, self)
        self.expense_dialog.save_button.clicked.connect(
            lambda _checked=False, expense_id=expense.id if expense else None: self._save_expense_dialog(
                self.expense_dialog, category_id, expense_id
            )
        )
        self.expense_dialog.show()
        self.expense_dialog.raise_()
        self.expense_dialog.activateWindow()

    def _restore_state(self, snapshot: LedgerState) -> None:
        self.service.state.categories[:] = snapshot.categories
        self.service.state.expenses[:] = snapshot.expenses
        self.service.state.budgets[:] = snapshot.budgets
        self.service.state.schema_version = snapshot.schema_version

    def _save_expense_dialog(self, dialog: ExpenseDialog, category_id: str, expense_id: str | None) -> None:
        snapshot = deepcopy(self.service.state)
        try:
            amount = dialog.amount_edit.text()
            date_value = dialog.date_edit.date().toString("yyyy-MM-dd")
            note = dialog.note_edit.text()
            if expense_id:
                self.service.update_expense(expense_id, amount, category_id, date_value, note)
            else:
                self.service.add_expense(amount, category_id, date_value, note)
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            dialog.error_label.setText(f"保存失败：{error}")
            return
        dialog.close()
        self.refresh_details()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("随手记")
    app.setFont(QFont("Microsoft YaHei UI", 11))
    style_path = Path(__file__).with_name("style.qss")
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))
    path = default_data_path()
    state = load_state(path)
    service = LedgerService(state)
    window = LedgerWindow(service, FileStore(path))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
