#!/usr/bin/env python3
"""Ubuntu verification GUI for the Cangjie ledger core."""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND = PROJECT_DIR / "target" / "release" / "bin" / "main"
DEFAULT_SDK = Path(
    "/home/zhangxxx/Documents/Codex/2026-10-23/referenced-chatgpt-conversation-this-is-an/outputs/cangjie-study/sdk/cangjie"
)


def build_command(backend: str | Path, args: list[str]) -> list[str]:
    """Build a subprocess argv list without invoking a shell."""

    return [str(backend), *args]


def _unescape(value: str) -> str:
    return value.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def parse_snapshot(snapshot: str) -> dict[str, object]:
    categories: list[dict[str, str]] = []
    expenses: list[dict[str, object]] = []
    budgets: dict[str, dict[str, object]] = {}
    for line in snapshot.splitlines():
        if not line or line.startswith("schemaVersion"):
            continue
        fields = line.split("\t")
        kind = fields[0]
        if kind == "C" and len(fields) == 6:
            categories.append(
                {
                    "id": _unescape(fields[1]),
                    "name": _unescape(fields[2]),
                    "parent_id": _unescape(fields[3]),
                    "created_at": _unescape(fields[4]),
                    "updated_at": _unescape(fields[5]),
                }
            )
        elif kind == "E" and len(fields) == 8:
            expenses.append(
                {
                    "id": _unescape(fields[1]),
                    "amount": int(fields[2]),
                    "category_id": _unescape(fields[3]),
                    "date": _unescape(fields[4]),
                    "note": _unescape(fields[5]),
                    "created_at": _unescape(fields[6]),
                    "updated_at": _unescape(fields[7]),
                }
            )
        elif kind == "B" and len(fields) == 4:
            month = _unescape(fields[1])
            budgets[month] = {
                "month": month,
                "amount": int(fields[2]),
                "updated_at": _unescape(fields[3]),
            }
        else:
            raise ValueError("数据快照格式损坏")
    return {"categories": categories, "expenses": expenses, "budgets": budgets}


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}¥{absolute // 100}.{absolute % 100:02d}"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class LedgerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("随手记 · V1.0")
        self.root.geometry("1120x720")
        self.root.minsize(900, 620)
        self.state: dict[str, object] = {"categories": [], "expenses": [], "budgets": {}}
        self.category_by_id: dict[str, dict[str, str]] = {}
        self.selected_expense: dict[str, object] | None = None
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.month_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.range_var = tk.StringVar(value="day")
        self.status_var = tk.StringVar(value="")
        self._build_layout()
        self.refresh()

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="随手记", font=("Sans", 24, "bold")).pack(side="left")
        ttk.Label(header, text="离线个人支出", foreground="#51605a").pack(side="left", padx=(12, 0), pady=(8, 0))
        ttk.Button(header, text="刷新", command=self.refresh).pack(side="right")
        ttk.Label(header, textvariable=self.status_var, foreground="#1d604b").pack(side="right", padx=12)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.detail_tab = ttk.Frame(self.notebook, padding=12)
        self.stats_tab = ttk.Frame(self.notebook, padding=12)
        self.budget_tab = ttk.Frame(self.notebook, padding=12)
        self.categories_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.detail_tab, text="明细")
        self.notebook.add(self.stats_tab, text="统计")
        self.notebook.add(self.budget_tab, text="预算")
        self.notebook.add(self.categories_tab, text="分类")
        self._build_detail_tab()
        self._build_stats_tab()
        self._build_budget_tab()
        self._build_categories_tab()

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Label(bottom, text="明细、统计、预算、分类").pack(side="left")
        ttk.Button(bottom, text="＋ 记一笔", command=self.open_category_picker).pack(side="right", ipadx=18, ipady=8)

    def _build_detail_tab(self) -> None:
        controls = ttk.Frame(self.detail_tab)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="查看范围").pack(side="left")
        ttk.Radiobutton(controls, text="单日", variable=self.range_var, value="day", command=self.refresh_detail).pack(side="left", padx=(10, 0))
        ttk.Radiobutton(controls, text="整月", variable=self.range_var, value="month", command=self.refresh_detail).pack(side="left")
        ttk.Label(controls, text="日期").pack(side="left", padx=(22, 4))
        date_entry = ttk.Entry(controls, textvariable=self.date_var, width=12)
        date_entry.pack(side="left")
        date_entry.bind("<Return>", lambda _event: self.refresh_detail())
        ttk.Label(controls, text="月份").pack(side="left", padx=(12, 4))
        month_entry = ttk.Entry(controls, textvariable=self.month_var, width=9)
        month_entry.pack(side="left")
        month_entry.bind("<Return>", lambda _event: self.refresh_detail())
        ttk.Button(controls, text="查询", command=self.refresh_detail).pack(side="left", padx=8)

        self.detail_total_var = tk.StringVar(value="¥0.00")
        self.detail_summary_var = tk.StringVar(value="暂无记录")
        summary = ttk.Frame(self.detail_tab)
        summary.pack(fill="x", pady=(0, 10))
        ttk.Label(summary, text="支出合计", foreground="#51605a").pack(side="left")
        ttk.Label(summary, textvariable=self.detail_total_var, font=("Sans", 22, "bold")).pack(side="left", padx=14)
        ttk.Label(summary, textvariable=self.detail_summary_var, foreground="#51605a").pack(side="left")

        table_frame = ttk.Frame(self.detail_tab)
        table_frame.pack(fill="both", expand=True)
        columns = ("date", "category", "amount", "note")
        self.expense_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"date": "日期", "category": "大类", "amount": "金额", "note": "备注"}
        widths = {"date": 120, "category": 130, "amount": 120, "note": 500}
        for key in columns:
            self.expense_tree.heading(key, text=headings[key])
            self.expense_tree.column(key, width=widths[key], anchor="e" if key == "amount" else "w")
        self.expense_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.expense_tree.yview)
        scroll.pack(side="right", fill="y")
        self.expense_tree.configure(yscrollcommand=scroll.set)
        self.expense_tree.bind("<<TreeviewSelect>>", self.on_expense_select)

        actions = ttk.Frame(self.detail_tab)
        actions.pack(fill="x", pady=(10, 0))
        self.detail_selection_var = tk.StringVar(value="选择一笔账单查看详情")
        ttk.Label(actions, textvariable=self.detail_selection_var).pack(side="left")
        ttk.Button(actions, text="编辑", command=self.edit_selected).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="删除", command=self.delete_selected).pack(side="right")

    def _build_stats_tab(self) -> None:
        top = ttk.Frame(self.stats_tab)
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="统计月份").pack(side="left")
        ttk.Entry(top, textvariable=self.month_var, width=10).pack(side="left", padx=6)
        ttk.Button(top, text="刷新统计", command=self.refresh_stats).pack(side="left")
        self.stats_total_var = tk.StringVar(value="¥0.00")
        self.stats_count_var = tk.StringVar(value="0 笔")
        self.stats_budget_var = tk.StringVar(value="")
        cards = ttk.Frame(self.stats_tab)
        cards.pack(fill="x", pady=(0, 16))
        ttk.Label(cards, text="月度支出", font=("Sans", 12)).pack(side="left")
        ttk.Label(cards, textvariable=self.stats_total_var, font=("Sans", 22, "bold")).pack(side="left", padx=14)
        ttk.Label(cards, textvariable=self.stats_count_var).pack(side="left", padx=14)
        ttk.Label(cards, textvariable=self.stats_budget_var, foreground="#8a4b2e").pack(side="left")
        self.stats_tree = ttk.Treeview(self.stats_tab, columns=("category", "amount", "ratio"), show="headings")
        for key, title, width in (("category", "大类", 220), ("amount", "金额", 180), ("ratio", "占比", 120)):
            self.stats_tree.heading(key, text=title)
            self.stats_tree.column(key, width=width, anchor="e" if key != "category" else "w")
        self.stats_tree.pack(fill="both", expand=True)

    def _build_budget_tab(self) -> None:
        form = ttk.Frame(self.budget_tab)
        form.pack(anchor="nw", fill="x")
        ttk.Label(form, text="月份（YYYY-MM）").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.month_var, width=12).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(form, text="总预算（元）").grid(row=1, column=0, sticky="w", pady=6)
        self.budget_input_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.budget_input_var, width=12).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(form, text="保存预算", command=self.save_budget).grid(row=1, column=2, padx=8)
        self.budget_status_var = tk.StringVar(value="尚未设置预算")
        ttk.Label(self.budget_tab, textvariable=self.budget_status_var, font=("Sans", 14)).pack(anchor="w", pady=(22, 8))
        self.budget_progress = ttk.Progressbar(self.budget_tab, orient="horizontal", length=520, mode="determinate", maximum=100)
        self.budget_progress.pack(anchor="w")
        self.budget_hint_var = tk.StringVar(value="")
        ttk.Label(self.budget_tab, textvariable=self.budget_hint_var, foreground="#51605a").pack(anchor="w", pady=8)

    def _build_categories_tab(self) -> None:
        self.category_tree = ttk.Treeview(self.categories_tab, columns=("name", "kind"), show="headings", selectmode="browse")
        self.category_tree.heading("name", text="分类名称")
        self.category_tree.heading("kind", text="层级")
        self.category_tree.column("name", width=260, anchor="w")
        self.category_tree.column("kind", width=120, anchor="w")
        self.category_tree.pack(side="left", fill="both", expand=True)
        self.category_tree.bind("<<TreeviewSelect>>", lambda _event: None)
        side = ttk.Frame(self.categories_tab, padding=(16, 0, 0, 0))
        side.pack(side="right", fill="y")
        ttk.Button(side, text="新增大类", command=lambda: self.add_category(False)).pack(fill="x", pady=4)
        ttk.Button(side, text="新增小类", command=lambda: self.add_category(True)).pack(fill="x", pady=4)
        ttk.Button(side, text="重命名选中", command=self.rename_category).pack(fill="x", pady=4)
        ttk.Label(side, text="先在左侧选择分类\n再执行新增小类或重命名", foreground="#51605a").pack(anchor="w", pady=18)

    def refresh(self) -> None:
        try:
            if not BACKEND.exists():
                raise RuntimeError("尚未找到仓颉可执行文件，请先运行 ./dev.sh build")
            result = subprocess.run(
                build_command(BACKEND, ["snapshot"]),
                cwd=PROJECT_DIR,
                env=self._backend_env(),
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stdout.strip() or result.stderr.strip() or "读取本地数据失败")
            self.state = parse_snapshot(result.stdout)
            self.category_by_id = {item["id"]: item for item in self.state["categories"]}  # type: ignore[index]
            self.refresh_detail()
            self.refresh_stats()
            self.refresh_budget()
            self.refresh_categories()
            self.status_var.set("数据已从本地保存加载")
        except Exception as exc:  # GUI boundary: keep the window usable after storage errors.
            self.status_var.set("读取失败")
            messagebox.showerror("读取失败", str(exc), parent=self.root)

    @staticmethod
    def _backend_env() -> dict[str, str]:
        env = os.environ.copy()
        sdk = Path(env.get("CANGJIE_HOME", str(DEFAULT_SDK)))
        runtime = sdk / "runtime" / "lib" / "linux_x86_64_cjnative"
        tools = sdk / "tools" / "lib"
        env["LD_LIBRARY_PATH"] = os.pathsep.join(str(path) for path in (runtime, tools, env.get("LD_LIBRARY_PATH", "")) if path)
        return env

    def _call(self, args: list[str]) -> str:
        result = subprocess.run(
            build_command(BACKEND, args),
            cwd=PROJECT_DIR,
            env=self._backend_env(),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stdout.strip() or result.stderr.strip() or "操作失败"
            raise RuntimeError(message.replace("ERROR\t", "", 1))
        return result.stdout.strip()

    def refresh_detail(self) -> None:
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)
        expenses = self.state["expenses"]  # type: ignore[assignment]
        if self.range_var.get() == "month":
            selected = [item for item in expenses if str(item["date"]).startswith(self.month_var.get())]
        else:
            selected = [item for item in expenses if item["date"] == self.date_var.get()]
        selected.sort(key=lambda item: (str(item["date"]), str(item["updated_at"]), str(item["id"])), reverse=True)
        total = sum(int(item["amount"]) for item in selected)
        self.detail_total_var.set(_money(total))
        self.detail_summary_var.set(f"{len(selected)} 笔" if selected else "暂无记录")
        for item in selected:
            category = self.category_by_id.get(str(item["category_id"]), {"name": "未知分类"})["name"]
            note = str(item["note"]) or "未填写备注"
            self.expense_tree.insert("", "end", iid=str(item["id"]), values=(item["date"], category, _money(int(item["amount"])), note))
        self.selected_expense = None
        self.detail_selection_var.set("选择一笔账单查看详情")

    def refresh_stats(self) -> None:
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        month = self.month_var.get()
        expenses = [item for item in self.state["expenses"] if str(item["date"]).startswith(month)]  # type: ignore[index]
        total = sum(int(item["amount"]) for item in expenses)
        self.stats_total_var.set(_money(total))
        self.stats_count_var.set(f"{len(expenses)} 笔")
        budget = self.state["budgets"].get(month)  # type: ignore[union-attr]
        self.stats_budget_var.set("")
        if budget:
            remaining = int(budget["amount"]) - total
            self.stats_budget_var.set((f"已超预算 {_money(-remaining)}" if remaining < 0 else f"剩余 {_money(remaining)}"))
        totals: dict[str, int] = {}
        for item in expenses:
            category_id = str(item["category_id"])
            totals[category_id] = totals.get(category_id, 0) + int(item["amount"])
        for category_id, amount in sorted(totals.items(), key=lambda pair: pair[1], reverse=True):
            category = self.category_by_id.get(category_id, {"name": "未知分类"})["name"]
            ratio = f"{amount / total * 100:.1f}%" if total else "0.0%"
            self.stats_tree.insert("", "end", values=(category, _money(amount), ratio))

    def refresh_budget(self) -> None:
        month = self.month_var.get()
        budget = self.state["budgets"].get(month)  # type: ignore[union-attr]
        spent = sum(int(item["amount"]) for item in self.state["expenses"] if str(item["date"]).startswith(month))  # type: ignore[index]
        if not budget:
            self.budget_status_var.set("尚未设置预算")
            self.budget_hint_var.set(f"{month} 已用 {_money(spent)}")
            self.budget_progress["value"] = 0
            self.budget_input_var.set("")
            return
        amount = int(budget["amount"])
        remaining = amount - spent
        self.budget_input_var.set(f"{amount / 100:.2f}")
        self.budget_status_var.set(f"预算 {_money(amount)}，已用 {_money(spent)}")
        self.budget_hint_var.set(f"{'已超预算 ' + _money(-remaining) if remaining < 0 else '剩余 ' + _money(remaining)}，使用比例 {spent / amount * 100:.0f}%")
        self.budget_progress["value"] = min(100, max(0, spent / amount * 100))

    def refresh_categories(self) -> None:
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        for category in self.state["categories"]:  # type: ignore[union-attr]
            if not category["parent_id"]:
                parent = self.category_tree.insert("", "end", iid=str(category["id"]), values=(category["name"], "大类"), open=True)
                for child in self.state["categories"]:  # type: ignore[union-attr]
                    if child["parent_id"] == category["id"]:
                        self.category_tree.insert(parent, "end", iid=str(child["id"]), values=(f"  {child['name']}", "小类"))

    def open_category_picker(self, on_selected: Callable[[dict[str, str]], None] | None = None) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("选择大类")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="先选择支出大类", font=("Sans", 14, "bold")).pack(padx=24, pady=(18, 10))
        for category in self.state["categories"]:  # type: ignore[union-attr]
            if category["parent_id"]:
                continue
            ttk.Button(dialog, text=category["name"], command=lambda c=category: self._category_chosen(dialog, c, on_selected)).pack(fill="x", padx=24, pady=4, ipadx=18, ipady=6)
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=(10, 18))

    def _category_chosen(self, dialog: tk.Toplevel, category: dict[str, str], callback: Callable[[dict[str, str]], None] | None) -> None:
        dialog.destroy()
        if callback:
            callback(category)
        else:
            self.open_expense_form(category)

    def open_expense_form(self, category: dict[str, str], expense: dict[str, object] | None = None) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑账单" if expense else "记一笔")
        dialog.transient(self.root)
        dialog.grab_set()
        amount_var = tk.StringVar(value=f"{int(expense['amount']) / 100:.2f}" if expense else "")
        date_var = tk.StringVar(value=str(expense["date"]) if expense else self.date_var.get())
        note_var = tk.StringVar(value=str(expense["note"]) if expense else "")
        category_var = tk.StringVar(value=str(category["name"]))
        error_var = tk.StringVar(value="")
        body = ttk.Frame(dialog, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="已选大类").grid(row=0, column=0, sticky="w", pady=7)
        ttk.Label(body, textvariable=category_var, font=("Sans", 12, "bold")).grid(row=0, column=1, sticky="w", pady=7)
        ttk.Button(body, text="重新选择", command=lambda: self.open_category_picker(lambda picked: (category.update(picked), category_var.set(picked["name"])))).grid(row=0, column=2, padx=8)
        ttk.Label(body, text="金额（元）").grid(row=1, column=0, sticky="w", pady=7)
        ttk.Entry(body, textvariable=amount_var, width=22).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="日期（YYYY-MM-DD）").grid(row=2, column=0, sticky="w", pady=7)
        ttk.Entry(body, textvariable=date_var, width=22).grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="备注／小类说明（选填）").grid(row=3, column=0, sticky="w", pady=7)
        ttk.Entry(body, textvariable=note_var, width=36).grid(row=3, column=1, columnspan=2, sticky="w")
        ttk.Label(body, textvariable=error_var, foreground="#a33b32").grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 12))

        def save() -> None:
            try:
                if expense:
                    self._call(["update-expense", str(expense["id"]), amount_var.get(), category["id"], date_var.get(), note_var.get(), _now()])
                else:
                    self._call(["add-expense", amount_var.get(), category["id"], date_var.get(), note_var.get(), _now()])
                dialog.destroy()
                self.refresh()
                self.status_var.set("账单已保存")
            except Exception as exc:
                error_var.set(str(exc))

        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, columnspan=3, sticky="e")
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="保存", command=save).pack(side="right", padx=4)

    def on_expense_select(self, _event: object) -> None:
        selection = self.expense_tree.selection()
        if not selection:
            return
        expense_id = selection[0]
        self.selected_expense = next((item for item in self.state["expenses"] if item["id"] == expense_id), None)  # type: ignore[index]
        if self.selected_expense:
            category = self.category_by_id.get(str(self.selected_expense["category_id"]), {"name": "未知分类"})["name"]
            self.detail_selection_var.set(f"{category} · {self.selected_expense['note'] or '未填写备注'}")

    def edit_selected(self) -> None:
        if not self.selected_expense:
            messagebox.showinfo("编辑账单", "请先选择一笔账单", parent=self.root)
            return
        category = self.category_by_id.get(str(self.selected_expense["category_id"]))
        if category:
            self.open_expense_form(category, self.selected_expense)

    def delete_selected(self) -> None:
        if not self.selected_expense:
            messagebox.showinfo("删除账单", "请先选择一笔账单", parent=self.root)
            return
        if not messagebox.askyesno("确认删除", "删除后无法从账本中恢复，确定继续吗？", parent=self.root):
            return
        try:
            self._call(["delete-expense", str(self.selected_expense["id"])])
            self.refresh()
            self.status_var.set("账单已删除")
        except Exception as exc:
            messagebox.showerror("删除失败", str(exc), parent=self.root)

    def save_budget(self) -> None:
        try:
            self._call(["set-budget", self.month_var.get(), self.budget_input_var.get(), _now()])
            self.refresh()
            self.status_var.set("预算已保存")
        except Exception as exc:
            messagebox.showerror("预算保存失败", str(exc), parent=self.root)

    def _selected_category(self) -> dict[str, str] | None:
        selection = self.category_tree.selection()
        if not selection:
            return None
        return self.category_by_id.get(selection[0])

    def add_category(self, child: bool) -> None:
        parent_id = ""
        if child:
            selected = self._selected_category()
            if not selected:
                messagebox.showinfo("新增小类", "请先选择一个大类", parent=self.root)
                return
            parent_id = selected["parent_id"] or selected["id"]
        self._category_name_dialog("新增分类", parent_id)

    def rename_category(self) -> None:
        selected = self._selected_category()
        if not selected:
            messagebox.showinfo("重命名分类", "请先选择一个分类", parent=self.root)
            return
        self._category_name_dialog("重命名分类", selected["parent_id"], selected)

    def _category_name_dialog(self, title: str, parent_id: str, existing: dict[str, str] | None = None) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        value = tk.StringVar(value=existing["name"] if existing else "")
        error = tk.StringVar(value="")
        body = ttk.Frame(dialog, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="分类名称").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=value, width=26).grid(row=0, column=1, pady=6)
        ttk.Label(body, textvariable=error, foreground="#a33b32").grid(row=1, column=0, columnspan=2, sticky="w")

        def save() -> None:
            try:
                if existing:
                    self._call(["rename-category", existing["id"], value.get(), _now()])
                else:
                    self._call(["add-category", value.get(), parent_id, _now()])
                dialog.destroy()
                self.refresh()
            except Exception as exc:
                error.set(str(exc))

        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="保存", command=save).pack(side="right", padx=4)


def main() -> None:
    root = tk.Tk()
    LedgerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
