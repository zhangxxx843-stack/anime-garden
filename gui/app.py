#!/usr/bin/env python3
"""Ubuntu verification GUI for the Cangjie ledger core."""

from __future__ import annotations

import os
import shutil
import subprocess
import tkinter as tk
import tkinter.font as tkfont
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


def expense_display_text(note: str, category_name: str) -> str:
    """Return the compact text shown in the expense list and selection card."""

    return note.strip() or category_name


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class LedgerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("随手记 · V1.0")
        self.root.geometry("1240x800")
        self.root.minsize(980, 680)
        self.colors = {
            "background": "#f7f4ee",
            "surface": "#ffffff",
            "surface_alt": "#edf5e9",
            "sidebar": "#163d31",
            "sidebar_muted": "#b8d0c1",
            "green": "#16784d",
            "green_dark": "#0f5e3d",
            "text": "#193029",
            "muted": "#6c7c74",
            "border": "#dbe3dc",
            "danger": "#a33b32",
        }
        self.ui_font = "TkDefaultFont"
        self._register_cjk_font()
        self.state: dict[str, object] = {"categories": [], "expenses": [], "budgets": {}}
        self.category_by_id: dict[str, dict[str, str]] = {}
        self.selected_expense: dict[str, object] | None = None
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.month_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.range_var = tk.StringVar(value="day")
        self.status_var = tk.StringVar(value="")
        self.detail_scope_title_var = tk.StringVar(value="今日支出")
        self.page_title_var = tk.StringVar(value="明细")
        self.page_subtitle_var = tk.StringVar(value="查看今天和本月的支出记录")
        self.nav_buttons: dict[str, tk.Button] = {}
        self.pages: dict[str, ttk.Frame] = {}
        self._build_layout()
        self.refresh()

    def _register_cjk_font(self) -> None:
        """Make the bundled Ubuntu Tk session use a real Chinese-capable font."""

        if os.name != "posix":
            return
        candidates = (
            PROJECT_DIR / ".cache" / "tk-fonts" / "wqy-zenhei.ttc",
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
            Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
        )
        source = next((path for path in candidates if path.exists()), None)
        xset = shutil.which("xset")
        mkfontscale = shutil.which("mkfontscale")
        mkfontdir = shutil.which("mkfontdir")
        if source is None or not xset or not mkfontscale or not mkfontdir:
            return
        font_dir = PROJECT_DIR / ".cache" / "tk-fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        target = font_dir / source.name
        if target.resolve() != source.resolve() and not target.exists():
            try:
                target.symlink_to(source)
            except OSError:
                return
        if not (font_dir / "fonts.dir").exists():
            subprocess.run([mkfontscale, str(font_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([mkfontdir, str(font_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([xset, "+fp", str(font_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([xset, "fp", "rehash"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        families = {family.casefold(): family for family in tkfont.families(self.root)}
        for family_name in ("wenquanyi zen hei", "droid sans fallback"):
            if family_name in families:
                self.ui_font = families[family_name]
                break

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        palette = self.colors
        style.configure("App.TFrame", background=palette["background"])
        style.configure("Surface.TFrame", background=palette["surface"])
        style.configure("SurfaceAlt.TFrame", background=palette["surface_alt"])
        style.configure("TLabel", background=palette["background"], foreground=palette["text"], font=(self.ui_font, 12))
        style.configure("Card.TLabel", background=palette["surface"], foreground=palette["text"], font=(self.ui_font, 12))
        style.configure("Muted.TLabel", background=palette["background"], foreground=palette["muted"], font=(self.ui_font, 12))
        style.configure("CardMuted.TLabel", background=palette["surface"], foreground=palette["muted"], font=(self.ui_font, 12))
        style.configure("Alt.TLabel", background=palette["surface_alt"], foreground=palette["text"], font=(self.ui_font, 12))
        style.configure("AltMuted.TLabel", background=palette["surface_alt"], foreground=palette["muted"], font=(self.ui_font, 12))
        style.configure("AltMoney.TLabel", background=palette["surface_alt"], foreground=palette["text"], font=(self.ui_font, 26, "bold"))
        style.configure("Heading.TLabel", background=palette["background"], foreground=palette["text"], font=(self.ui_font, 18, "bold"))
        style.configure("CardHeading.TLabel", background=palette["surface"], foreground=palette["text"], font=(self.ui_font, 13, "bold"))
        style.configure("Money.TLabel", background=palette["surface_alt"], foreground=palette["text"], font=(self.ui_font, 25, "bold"))
        style.configure("Accent.TButton", background=palette["green"], foreground="#ffffff", padding=(15, 9), borderwidth=0, font=(self.ui_font, 12, "bold"))
        style.map("Accent.TButton", background=[("active", palette["green_dark"]), ("pressed", palette["green_dark"])])
        style.configure("Quiet.TButton", background=palette["surface"], foreground=palette["text"], padding=(12, 8), borderwidth=0, font=(self.ui_font, 12))
        style.map("Quiet.TButton", background=[("active", palette["surface_alt"])])
        style.configure("TRadiobutton", background=palette["surface"], foreground=palette["text"], font=(self.ui_font, 12))
        style.configure("TEntry", font=(self.ui_font, 12), padding=5)
        style.configure("Treeview", background=palette["surface"], fieldbackground=palette["surface"], foreground=palette["text"], rowheight=46, borderwidth=0, font=(self.ui_font, 12))
        style.configure("Treeview.Heading", background=palette["surface"], foreground=palette["muted"], font=(self.ui_font, 12, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#dcefe0")], foreground=[("selected", palette["text"])])
        style.configure("Horizontal.TProgressbar", background=palette["green"], troughcolor="#dfe8df", borderwidth=0, lightcolor=palette["green"], darkcolor=palette["green"])

    def _card(self, parent: tk.Misc, style: str = "Surface.TFrame") -> ttk.Frame:
        return ttk.Frame(parent, style=style, padding=18)

    def _build_layout(self) -> None:
        self._configure_styles()
        self.root.configure(bg=self.colors["background"])
        shell = tk.Frame(self.root, bg=self.colors["background"])
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg=self.colors["sidebar"], width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="随手记", bg=self.colors["sidebar"], fg="#ffffff", font=(self.ui_font, 26, "bold")).pack(anchor="w", padx=26, pady=(34, 2))
        tk.Label(sidebar, text="离线个人支出", bg=self.colors["sidebar"], fg=self.colors["sidebar_muted"], font=(self.ui_font, 12)).pack(anchor="w", padx=28, pady=(0, 30))
        add_button = tk.Button(
            sidebar,
            text="＋  记一笔",
            command=self.open_category_picker,
            bg=self.colors["green"],
            fg="#ffffff",
            activebackground=self.colors["green_dark"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            highlightthickness=0,
            overrelief="flat",
            cursor="hand2",
            font=(self.ui_font, 13, "bold"),
            padx=14,
            pady=12,
        )
        add_button.pack(fill="x", padx=22, pady=(0, 28))
        nav_items = [
            ("detail", "明细"),
            ("stats", "统计"),
            ("budget", "预算"),
            ("categories", "分类"),
        ]
        for key, label in nav_items:
            button = tk.Button(
                sidebar,
                text=f"    {label}",
                command=lambda page=key: self.show_page(page),
                anchor="w",
                bg=self.colors["sidebar"],
                fg="#e7f0e9",
                activebackground="#285846",
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                highlightthickness=0,
                overrelief="flat",
                cursor="hand2",
                font=(self.ui_font, 12),
                padx=12,
                pady=11,
            )
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = button
        tk.Frame(sidebar, bg=self.colors["sidebar"]).pack(fill="both", expand=True)
        tk.Label(sidebar, text="Ubuntu 试用版", bg=self.colors["sidebar"], fg=self.colors["sidebar_muted"], font=(self.ui_font, 10)).pack(anchor="w", padx=28, pady=(0, 4))
        tk.Label(sidebar, text="数据保存在本地", bg=self.colors["sidebar"], fg="#8eada0", font=(self.ui_font, 10)).pack(anchor="w", padx=28, pady=(0, 24))

        content = ttk.Frame(shell, style="App.TFrame", padding=(32, 26, 32, 28))
        content.pack(side="left", fill="both", expand=True)
        header = ttk.Frame(content, style="App.TFrame")
        header.pack(fill="x", pady=(0, 20))
        heading = ttk.Frame(header, style="App.TFrame")
        heading.pack(side="left")
        ttk.Label(heading, textvariable=self.page_title_var, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(heading, textvariable=self.page_subtitle_var, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        actions = ttk.Frame(header, style="App.TFrame")
        actions.pack(side="right", anchor="n")
        ttk.Label(actions, textvariable=self.status_var, style="Muted.TLabel").pack(side="left", padx=(0, 12), pady=8)
        ttk.Button(actions, text="↻ 刷新", style="Quiet.TButton", command=self.refresh).pack(side="left")

        self.page_container = ttk.Frame(content, style="App.TFrame")
        self.page_container.pack(fill="both", expand=True)
        self.detail_tab = ttk.Frame(self.page_container, style="App.TFrame")
        self.stats_tab = ttk.Frame(self.page_container, style="App.TFrame")
        self.budget_tab = ttk.Frame(self.page_container, style="App.TFrame")
        self.categories_tab = ttk.Frame(self.page_container, style="App.TFrame")
        self.pages = {"detail": self.detail_tab, "stats": self.stats_tab, "budget": self.budget_tab, "categories": self.categories_tab}
        self._build_detail_tab()
        self._build_stats_tab()
        self._build_budget_tab()
        self._build_categories_tab()
        self.show_page("detail")

    def show_page(self, page: str) -> None:
        for frame in self.pages.values():
            frame.pack_forget()
        self.pages[page].pack(fill="both", expand=True)
        titles = {
            "detail": ("明细", "查看今天和本月的支出记录"),
            "stats": ("统计", "按月份查看支出构成与占比"),
            "budget": ("预算", "设置每月预算并跟踪使用情况"),
            "categories": ("分类", "管理大类和自定义小类"),
        }
        self.page_title_var.set(titles[page][0])
        self.page_subtitle_var.set(titles[page][1])
        for key, button in self.nav_buttons.items():
            button.configure(bg="#285846" if key == page else self.colors["sidebar"], fg="#ffffff" if key == page else "#e7f0e9")

    def _build_detail_tab(self) -> None:
        controls = self._card(self.detail_tab)
        controls.pack(fill="x", pady=(0, 14))
        ttk.Label(controls, text="查看范围", style="Card.TLabel", font=(self.ui_font, 12, "bold")).pack(side="left")
        ttk.Radiobutton(controls, text="单日", variable=self.range_var, value="day", command=self.refresh_detail).pack(side="left", padx=(14, 0))
        ttk.Radiobutton(controls, text="整月", variable=self.range_var, value="month", command=self.refresh_detail).pack(side="left")
        ttk.Label(controls, text="日期", style="CardMuted.TLabel").pack(side="left", padx=(26, 4))
        date_entry = ttk.Entry(controls, textvariable=self.date_var, width=12)
        date_entry.pack(side="left")
        date_entry.bind("<Return>", lambda _event: self.refresh_detail())
        ttk.Label(controls, text="月份", style="CardMuted.TLabel").pack(side="left", padx=(14, 4))
        month_entry = ttk.Entry(controls, textvariable=self.month_var, width=9)
        month_entry.pack(side="left")
        month_entry.bind("<Return>", lambda _event: self.refresh_detail())
        ttk.Button(controls, text="查询", style="Quiet.TButton", command=self.refresh_detail).pack(side="left", padx=10)

        self.detail_total_var = tk.StringVar(value="¥0.00")
        self.detail_summary_var = tk.StringVar(value="暂无记录")
        summary = self._card(self.detail_tab, "SurfaceAlt.TFrame")
        summary.pack(fill="x", pady=(0, 14))
        ttk.Label(summary, textvariable=self.detail_scope_title_var, style="AltMuted.TLabel").pack(anchor="w")
        summary_row = ttk.Frame(summary, style="SurfaceAlt.TFrame")
        summary_row.pack(fill="x", pady=(3, 0))
        ttk.Label(summary_row, textvariable=self.detail_total_var, style="AltMoney.TLabel").pack(side="left")
        ttk.Label(summary_row, textvariable=self.detail_summary_var, style="AltMuted.TLabel").pack(side="right", anchor="s", pady=(0, 5))

        table_frame = self._card(self.detail_tab)
        table_frame.pack(fill="both", expand=True)
        ttk.Label(table_frame, text="账单记录", style="CardHeading.TLabel").pack(anchor="w", pady=(0, 10))
        columns = ("date", "content", "amount")
        self.expense_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"date": "日期", "content": "账单内容", "amount": "金额"}
        widths = {"date": 150, "content": 520, "amount": 150}
        for key in columns:
            anchor = "e" if key == "amount" else "w"
            self.expense_tree.heading(key, text=headings[key], anchor=anchor)
            self.expense_tree.column(key, width=widths[key], minwidth=widths[key], anchor=anchor, stretch=key == "content")
        self.expense_tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.expense_tree.yview)
        scroll.pack(side="right", fill="y")
        self.expense_tree.configure(yscrollcommand=scroll.set)
        self.expense_tree.bind("<<TreeviewSelect>>", self.on_expense_select)
        self.detail_empty_label = ttk.Label(
            table_frame,
            text="当前时间范围暂无记录\n点击左侧“＋ 记一笔”开始记录",
            style="CardMuted.TLabel",
            justify="center",
        )
        self.detail_empty_label.place(relx=0.5, rely=0.56, anchor="center")

        actions = ttk.Frame(self.detail_tab, style="App.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        self.detail_selection_var = tk.StringVar(value="选择一笔账单查看详情")
        ttk.Label(actions, textvariable=self.detail_selection_var, style="Muted.TLabel").pack(side="left")
        ttk.Button(actions, text="编辑", style="Quiet.TButton", command=self.edit_selected).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="删除", style="Quiet.TButton", command=self.delete_selected).pack(side="right")

    def _build_stats_tab(self) -> None:
        top = self._card(self.stats_tab)
        top.pack(fill="x", pady=(0, 14))
        ttk.Label(top, text="统计月份", style="Card.TLabel", font=(self.ui_font, 12, "bold")).pack(side="left")
        ttk.Entry(top, textvariable=self.month_var, width=10).pack(side="left", padx=6)
        ttk.Button(top, text="刷新统计", style="Quiet.TButton", command=self.refresh_stats).pack(side="left")
        self.stats_total_var = tk.StringVar(value="¥0.00")
        self.stats_count_var = tk.StringVar(value="0 笔")
        self.stats_budget_var = tk.StringVar(value="")
        cards = self._card(self.stats_tab, "SurfaceAlt.TFrame")
        cards.pack(fill="x", pady=(0, 14))
        ttk.Label(cards, text="本月支出", style="AltMuted.TLabel").pack(anchor="w")
        stats_row = ttk.Frame(cards, style="SurfaceAlt.TFrame")
        stats_row.pack(fill="x", pady=(3, 0))
        ttk.Label(stats_row, textvariable=self.stats_total_var, style="AltMoney.TLabel").pack(side="left")
        ttk.Label(stats_row, textvariable=self.stats_count_var, style="AltMuted.TLabel").pack(side="left", padx=22, pady=(12, 0))
        ttk.Label(stats_row, textvariable=self.stats_budget_var, style="AltMuted.TLabel").pack(side="right", pady=(12, 0))
        table = self._card(self.stats_tab)
        table.pack(fill="both", expand=True)
        ttk.Label(table, text="分类构成", style="CardHeading.TLabel").pack(anchor="w", pady=(0, 10))
        self.stats_tree = ttk.Treeview(table, columns=("category", "amount", "ratio"), show="headings")
        for key, title, width in (("category", "大类", 220), ("amount", "金额", 180), ("ratio", "占比", 120)):
            self.stats_tree.heading(key, text=title)
            self.stats_tree.column(key, width=width, anchor="e" if key != "category" else "w")
        self.stats_tree.pack(fill="both", expand=True)

    def _build_budget_tab(self) -> None:
        card = self._card(self.budget_tab)
        card.pack(fill="x", pady=(0, 14))
        ttk.Label(card, text="月度预算", style="CardHeading.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))
        form = ttk.Frame(card, style="Surface.TFrame")
        form.grid(row=1, column=0, columnspan=3, sticky="ew")
        ttk.Label(form, text="月份（YYYY-MM）", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.month_var, width=12).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(form, text="总预算（元）", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        self.budget_input_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.budget_input_var, width=12).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(form, text="保存预算", style="Accent.TButton", command=self.save_budget).grid(row=1, column=2, padx=8)
        self.budget_status_var = tk.StringVar(value="尚未设置预算")
        ttk.Label(card, textvariable=self.budget_status_var, style="CardHeading.TLabel", font=(self.ui_font, 15)).grid(row=2, column=0, columnspan=3, sticky="w", pady=(24, 8))
        self.budget_progress = ttk.Progressbar(card, orient="horizontal", length=520, mode="determinate", maximum=100)
        self.budget_progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        self.budget_hint_var = tk.StringVar(value="")
        ttk.Label(card, textvariable=self.budget_hint_var, style="CardMuted.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        card.columnconfigure(1, weight=1)

    def _build_categories_tab(self) -> None:
        card = self._card(self.categories_tab)
        card.pack(fill="both", expand=True)
        top = ttk.Frame(card, style="Surface.TFrame")
        top.pack(fill="x", pady=(0, 12))
        ttk.Label(top, text="分类管理", style="CardHeading.TLabel").pack(side="left")
        ttk.Button(top, text="新增大类", style="Accent.TButton", command=lambda: self.add_category(False)).pack(side="right")
        self.category_tree = ttk.Treeview(card, columns=("name", "kind"), show="headings", selectmode="browse")
        self.category_tree.heading("name", text="分类名称")
        self.category_tree.heading("kind", text="层级")
        self.category_tree.column("name", width=260, anchor="w")
        self.category_tree.column("kind", width=120, anchor="w")
        self.category_tree.pack(side="left", fill="both", expand=True)
        self.category_tree.bind("<<TreeviewSelect>>", lambda _event: None)
        side = ttk.Frame(card, style="Surface.TFrame", padding=(18, 0, 0, 0))
        side.pack(side="right", fill="y")
        ttk.Button(side, text="新增小类", style="Quiet.TButton", command=lambda: self.add_category(True)).pack(fill="x", pady=4)
        ttk.Button(side, text="重命名选中", style="Quiet.TButton", command=self.rename_category).pack(fill="x", pady=4)
        ttk.Label(side, text="先选择左侧分类\n再新增小类或重命名", style="CardMuted.TLabel", justify="left").pack(anchor="w", pady=18)

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
            self.detail_scope_title_var.set("本月支出")
            selected = [item for item in expenses if str(item["date"]).startswith(self.month_var.get())]
        else:
            self.detail_scope_title_var.set("今日支出")
            selected = [item for item in expenses if item["date"] == self.date_var.get()]
        selected.sort(key=lambda item: (str(item["date"]), str(item["updated_at"]), str(item["id"])), reverse=True)
        total = sum(int(item["amount"]) for item in selected)
        self.detail_total_var.set(_money(total))
        self.detail_summary_var.set(f"{len(selected)} 笔" if selected else "暂无记录")
        if selected:
            self.detail_empty_label.place_forget()
        else:
            self.detail_empty_label.place(relx=0.5, rely=0.56, anchor="center")
        for item in selected:
            category = self.category_by_id.get(str(item["category_id"]), {"name": "未知分类"})["name"]
            content = expense_display_text(str(item["note"]), category)
            self.expense_tree.insert("", "end", iid=str(item["id"]), values=(item["date"], content, _money(int(item["amount"]))))
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
        dialog.geometry("430x470")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="选择支出大类", style="Heading.TLabel").pack(anchor="w", padx=28, pady=(26, 4))
        ttk.Label(dialog, text="选好分类后继续填写金额和日期", style="Muted.TLabel").pack(anchor="w", padx=28, pady=(0, 18))
        list_card = self._card(dialog)
        list_card.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        for category in self.state["categories"]:  # type: ignore[union-attr]
            if category["parent_id"]:
                continue
            ttk.Button(list_card, text=f"  {category['name']}   >", style="Quiet.TButton", command=lambda c=category: self._category_chosen(dialog, c, on_selected)).pack(fill="x", pady=4, ipady=6)
        ttk.Button(dialog, text="取消", style="Quiet.TButton", command=dialog.destroy).pack(pady=(0, 20))

    def _category_chosen(self, dialog: tk.Toplevel, category: dict[str, str], callback: Callable[[dict[str, str]], None] | None) -> None:
        dialog.destroy()
        if callback:
            callback(category)
        else:
            self.open_expense_form(category)

    def open_expense_form(self, category: dict[str, str], expense: dict[str, object] | None = None) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑账单" if expense else "记一笔")
        dialog.geometry("560x520")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        amount_var = tk.StringVar(value=f"{int(expense['amount']) / 100:.2f}" if expense else "")
        date_var = tk.StringVar(value=str(expense["date"]) if expense else self.date_var.get())
        note_var = tk.StringVar(value=str(expense["note"]) if expense else "")
        category_var = tk.StringVar(value=str(category["name"]))
        error_var = tk.StringVar(value="")
        ttk.Label(dialog, text="编辑账单" if expense else "记一笔", style="Heading.TLabel").pack(anchor="w", padx=28, pady=(24, 2))
        ttk.Label(dialog, text="记录一笔离线支出", style="Muted.TLabel").pack(anchor="w", padx=28, pady=(0, 16))
        body = self._card(dialog)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        ttk.Label(body, text="已选大类", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Label(body, textvariable=category_var, style="CardHeading.TLabel").grid(row=0, column=1, sticky="w", pady=8)
        ttk.Button(
            body,
            text="重新选择",
            style="Quiet.TButton",
            command=lambda: self.open_category_picker(lambda picked: (category.update(picked), category_var.set(picked["name"]))),
        ).grid(row=0, column=2, padx=8)
        ttk.Label(body, text="金额（元）", style="CardMuted.TLabel").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(body, textvariable=amount_var, width=22).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="日期（YYYY-MM-DD）", style="CardMuted.TLabel").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Entry(body, textvariable=date_var, width=22).grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="备注／小类说明（选填）", style="CardMuted.TLabel").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(body, textvariable=note_var, width=36).grid(row=3, column=1, columnspan=2, sticky="w")
        ttk.Label(body, textvariable=error_var, foreground=self.colors["danger"], background=self.colors["surface"]).grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 12))

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
        ttk.Button(buttons, text="取消", style="Quiet.TButton", command=dialog.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="保存", style="Accent.TButton", command=save).pack(side="right", padx=4)

    def on_expense_select(self, _event: object) -> None:
        selection = self.expense_tree.selection()
        if not selection:
            return
        expense_id = selection[0]
        self.selected_expense = next((item for item in self.state["expenses"] if item["id"] == expense_id), None)  # type: ignore[index]
        if self.selected_expense:
            category = self.category_by_id.get(str(self.selected_expense["category_id"]), {"name": "未知分类"})["name"]
            content = expense_display_text(str(self.selected_expense["note"]), category)
            self.detail_selection_var.set(content)

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
        dialog.geometry("430x250")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        value = tk.StringVar(value=existing["name"] if existing else "")
        error = tk.StringVar(value="")
        ttk.Label(dialog, text=title, style="Heading.TLabel").pack(anchor="w", padx=28, pady=(24, 2))
        ttk.Label(dialog, text="名称不能为空，且同层级不能重复", style="Muted.TLabel").pack(anchor="w", padx=28, pady=(0, 16))
        body = self._card(dialog)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="分类名称", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(body, textvariable=value, width=26).grid(row=0, column=1, pady=6)
        ttk.Label(body, textvariable=error, foreground=self.colors["danger"], background=self.colors["surface"]).grid(row=1, column=0, columnspan=2, sticky="w")

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
        ttk.Button(buttons, text="取消", style="Quiet.TButton", command=dialog.destroy).pack(side="right", padx=4)
        ttk.Button(buttons, text="保存", style="Accent.TButton", command=save).pack(side="right", padx=4)


def main() -> None:
    root = tk.Tk()
    LedgerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
