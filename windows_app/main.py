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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QDateEdit,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ledger_domain import LedgerService, LedgerState, expense_display_text
from .ledger_storage import default_data_path, deserialize_state, load_state, save_state


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
        self.import_button = QPushButton("导入旧账本")
        self.import_button.setObjectName("secondaryButton")
        self.import_button.clicked.connect(self.import_ledger)
        sidebar_layout.addWidget(self.import_button)
        self.add_button = QPushButton("＋ 记一笔")
        self.add_button.setObjectName("primaryAddButton")
        self.add_button.clicked.connect(self.open_add_expense)
        sidebar_layout.addWidget(self.add_button)
        root_layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_details_page())
        self.pages.addWidget(self._build_stats_page())
        self.pages.addWidget(self._build_budget_page())
        self.pages.addWidget(self._build_categories_page())
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
        self.edit_button = QPushButton("编辑")
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected_expense)
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("secondaryButton")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_expense)
        header.addWidget(self.edit_button)
        header.addWidget(self.delete_button)
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
        self.expense_table.itemSelectionChanged.connect(self._update_expense_actions)
        table_layout.addWidget(self.expense_table)
        layout.addWidget(table_frame, 1)
        return page

    def _build_stats_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("统计")
        title.setObjectName("pageTitle")
        hint = QLabel("按月查看总支出与分类分布")
        hint.setObjectName("pageHint")
        title_box.addWidget(title)
        title_box.addWidget(hint)
        header.addLayout(title_box)
        header.addStretch(1)
        self.stats_month_filter = QDateEdit(QDate.currentDate())
        self.stats_month_filter.setDisplayFormat("yyyy-MM")
        self.stats_month_filter.setCalendarPopup(True)
        self.stats_month_filter.dateChanged.connect(self.refresh_stats)
        header.addWidget(QLabel("月份"))
        header.addWidget(self.stats_month_filter)
        layout.addLayout(header)

        cards = QHBoxLayout()
        self.stats_total_card = self._summary_card("月度支出", "¥0.00")
        self.stats_count_card = self._summary_card("记录笔数", "0 笔")
        self.stats_total_label = self.stats_total_card.value_label
        self.stats_count_label = self.stats_count_card.value_label
        cards.addWidget(self.stats_total_card)
        cards.addWidget(self.stats_count_card)
        cards.addStretch(1)
        layout.addLayout(cards)

        self.stats_table = QTableWidget(0, 2)
        self.stats_table.setHorizontalHeaderLabels(["分类", "金额"])
        self.stats_table.setObjectName("expenseTable")
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.stats_table, 1)
        return page

    def _build_budget_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        title = QLabel("预算")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel("设置每月预算，随时看到剩余金额")
        hint.setObjectName("pageHint")
        layout.addWidget(hint)

        panel = QFrame()
        panel.setObjectName("summaryCard")
        form = QFormLayout(panel)
        form.setContentsMargins(24, 22, 24, 22)
        self.budget_month_edit = QDateEdit(QDate.currentDate())
        self.budget_month_edit.setDisplayFormat("yyyy-MM")
        self.budget_month_edit.setCalendarPopup(True)
        self.budget_month_edit.dateChanged.connect(self.refresh_budget)
        self.budget_amount_edit = QLineEdit()
        self.budget_amount_edit.setPlaceholderText("例如 3000")
        self.budget_save_button = QPushButton("保存预算")
        self.budget_save_button.setObjectName("primaryButton")
        self.budget_save_button.clicked.connect(self.save_budget)
        form.addRow("月份", self.budget_month_edit)
        form.addRow("预算金额", self.budget_amount_edit)
        form.addRow("", self.budget_save_button)
        layout.addWidget(panel)

        self.budget_progress = QProgressBar()
        self.budget_progress.setRange(0, 100)
        self.budget_progress.setTextVisible(True)
        layout.addWidget(self.budget_progress)
        self.budget_status_label = QLabel("")
        self.budget_status_label.setObjectName("budgetStatus")
        layout.addWidget(self.budget_status_label)
        layout.addStretch(1)
        return page

    def _build_categories_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        title = QLabel("分类")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        hint = QLabel("维护大类和小类，记账时会立即可用")
        hint.setObjectName("pageHint")
        layout.addWidget(hint)

        body = QHBoxLayout()
        self.category_list = QListWidget()
        self.category_list.setObjectName("categoryList")
        self.category_list.currentItemChanged.connect(self._category_selection_changed)
        body.addWidget(self.category_list, 1)

        editor = QFrame()
        editor.setObjectName("summaryCard")
        editor_layout = QFormLayout(editor)
        editor_layout.setContentsMargins(24, 22, 24, 22)
        self.category_name_edit = QLineEdit()
        self.category_name_edit.setPlaceholderText("例如 早餐")
        self.category_parent_combo = QComboBox()
        self.category_add_button = QPushButton("新增分类")
        self.category_add_button.setObjectName("primaryButton")
        self.category_add_button.clicked.connect(self.add_category)
        self.category_rename_button = QPushButton("重命名所选")
        self.category_rename_button.setObjectName("secondaryButton")
        self.category_rename_button.clicked.connect(self.rename_category)
        self.category_error_label = QLabel("")
        self.category_error_label.setObjectName("errorLabel")
        self.category_error_label.setWordWrap(True)
        editor_layout.addRow("名称", self.category_name_edit)
        editor_layout.addRow("上级大类", self.category_parent_combo)
        editor_layout.addRow("", self.category_add_button)
        editor_layout.addRow("", self.category_rename_button)
        editor_layout.addRow("", self.category_error_label)
        body.addWidget(editor, 1)
        layout.addLayout(body, 1)
        self.refresh_categories()
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
        elif page_key == "stats":
            self.refresh_stats()
        elif page_key == "budget":
            self.refresh_budget()
        elif page_key == "categories":
            self.refresh_categories()

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
        self._visible_expenses = expenses
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
        self._update_expense_actions()

    def _update_expense_actions(self) -> None:
        enabled = hasattr(self, "expense_table") and self.expense_table.currentRow() >= 0
        if hasattr(self, "edit_button"):
            self.edit_button.setEnabled(enabled)
        if hasattr(self, "delete_button"):
            self.delete_button.setEnabled(enabled)

    def _selected_expense(self):
        row = self.expense_table.currentRow()
        if row < 0 or row >= len(getattr(self, "_visible_expenses", [])):
            return None
        return self._visible_expenses[row]

    def edit_selected_expense(self) -> None:
        expense = self._selected_expense()
        if expense is not None:
            self.open_expense_dialog(expense.category_id, expense)

    def delete_selected_expense(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        answer = QMessageBox.question(self, "删除记录", "确定删除这笔支出吗？")
        if answer != QMessageBox.Yes:
            return
        snapshot = deepcopy(self.service.state)
        try:
            self.service.delete_expense(expense.id)
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            QMessageBox.warning(self, "保存失败", f"删除没有保存成功：{error}")
            return
        self.refresh_details()

    def refresh_stats(self) -> None:
        if not hasattr(self, "stats_table"):
            return
        month = self.stats_month_filter.date().toString("yyyy-MM")
        summary = self.service.summarize_month(month)
        self.stats_total_label.setText(money(summary["total_cents"]))
        self.stats_count_label.setText(f"{summary['count']} 笔")
        rows = []
        for category_id, total in summary["by_category"].items():
            category = next((item for item in self.service.state.categories if item.id == category_id), None)
            rows.append((category.name if category else "未分类", total))
        rows.sort(key=lambda item: item[1], reverse=True)
        self.stats_table.setRowCount(len(rows))
        for row, (category_name, total) in enumerate(rows):
            self.stats_table.setItem(row, 0, QTableWidgetItem(category_name))
            amount_item = QTableWidgetItem(money(total))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.stats_table.setItem(row, 1, amount_item)

    def refresh_budget(self) -> None:
        if not hasattr(self, "budget_progress"):
            return
        month = self.budget_month_edit.date().toString("yyyy-MM")
        status = self.service.budget_status(month)
        current_budget = next((budget for budget in self.service.state.budgets if budget.month == month), None)
        self.budget_amount_edit.blockSignals(True)
        self.budget_amount_edit.setText(f"{current_budget.amount_cents / 100:.2f}" if current_budget else "")
        self.budget_amount_edit.blockSignals(False)
        if status["budget_cents"]:
            progress = min(100, round(status["spent_cents"] * 100 / status["budget_cents"]))
            self.budget_progress.setValue(progress)
            if status["over_budget"]:
                self.budget_status_label.setText(
                    f"已用 {money(status['spent_cents'])}，超出 {money(-status['remaining_cents'])}"
                )
            else:
                self.budget_status_label.setText(
                    f"已用 {money(status['spent_cents'])}，剩余 {money(status['remaining_cents'])}"
                )
        else:
            self.budget_progress.setValue(0)
            self.budget_status_label.setText("本月尚未设置预算")

    def save_budget(self) -> None:
        month = self.budget_month_edit.date().toString("yyyy-MM")
        snapshot = deepcopy(self.service.state)
        try:
            self.service.set_budget(month, self.budget_amount_edit.text())
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            self.budget_status_label.setText(f"保存失败：{error}")
            return
        self.refresh_budget()

    def refresh_categories(self) -> None:
        if not hasattr(self, "category_list"):
            return
        selected_id = None
        current = self.category_list.currentItem()
        if current is not None:
            selected_id = current.data(Qt.UserRole)
        self.category_list.blockSignals(True)
        self.category_list.clear()
        for category in self.service.state.categories:
            item = QListWidgetItem(category.name)
            item.setData(Qt.UserRole, category.id)
            if category.parent_id:
                item.setToolTip("上级：" + self._category_name(category.parent_id))
            self.category_list.addItem(item)
        self.category_list.blockSignals(False)
        self.category_parent_combo.blockSignals(True)
        self.category_parent_combo.clear()
        self.category_parent_combo.addItem("无（大类）", None)
        for category in self.service.state.categories:
            self.category_parent_combo.addItem(category.name, category.id)
        self.category_parent_combo.blockSignals(False)
        if selected_id:
            for row in range(self.category_list.count()):
                if self.category_list.item(row).data(Qt.UserRole) == selected_id:
                    self.category_list.setCurrentRow(row)
                    break

    def _category_name(self, category_id: str) -> str:
        category = next((item for item in self.service.state.categories if item.id == category_id), None)
        return category.name if category else "未分类"

    def _category_selection_changed(self, current, _previous) -> None:
        if current is None:
            return
        category_id = current.data(Qt.UserRole)
        category = next(item for item in self.service.state.categories if item.id == category_id)
        self.category_name_edit.setText(category.name)
        index = self.category_parent_combo.findData(category.parent_id)
        self.category_parent_combo.setCurrentIndex(max(index, 0))

    def add_category(self) -> None:
        snapshot = deepcopy(self.service.state)
        try:
            self.service.add_category(
                self.category_name_edit.text(),
                self.category_parent_combo.currentData(),
            )
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            self.category_error_label.setText(f"保存失败：{error}")
            return
        self.category_error_label.setText("")
        self.category_name_edit.clear()
        self.refresh_categories()

    def rename_category(self) -> None:
        current = self.category_list.currentItem()
        if current is None:
            self.category_error_label.setText("请先选择要重命名的分类")
            return
        snapshot = deepcopy(self.service.state)
        try:
            self.service.rename_category(current.data(Qt.UserRole), self.category_name_edit.text())
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            self.category_error_label.setText(f"保存失败：{error}")
            return
        self.category_error_label.setText("")
        self.refresh_categories()

    def import_ledger(self, path=None) -> bool:
        if path is None:
            selected_path, _filter = QFileDialog.getOpenFileName(
                self, "导入旧账本", str(Path.home()), "账本文件 (*.tsv);;所有文件 (*)"
            )
            path = selected_path
        if not path:
            return False
        try:
            imported = deserialize_state(Path(path).read_text(encoding="utf-8"))
        except Exception as error:
            self.details_hint.setText(f"导入失败：{error}")
            return False
        snapshot = deepcopy(self.service.state)
        try:
            self._restore_state(imported)
            self.store.save(self.service.state)
        except Exception as error:
            self._restore_state(snapshot)
            self.details_hint.setText(f"导入失败：{error}")
            return False
        self.refresh_details()
        self.refresh_stats()
        self.refresh_budget()
        self.refresh_categories()
        return True

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
