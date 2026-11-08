# Windows Desktop V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, offline Windows desktop version of “随手记” that packages as a runnable x64 executable while preserving the validated Cangjie course core.

**Architecture:** Add a self-contained Python/PySide6 Windows client. Its domain and TSV storage adapter mirror the Cangjie schema version 1 and run directly in the packaged client, so the end user does not need Cangjie. Keep the existing Cangjie model/service/storage/protocol and tests as the course reference implementation; the Windows client is tested against the same business rules and file format.

**Tech Stack:** Python 3.12, PySide6, Python `unittest`, PyInstaller, GitHub Actions `windows-latest`, Cangjie 1.0.5 reference core.

**Spec:** `docs/superpowers/specs/2026-11-08-windows-desktop-v1-design.md`

## Global Constraints

- The Windows target is Windows 10/11 x64.
- The packaged client must run without a Cangjie SDK, Python installation, or network connection.
- Amounts use integer cents and dates use local `YYYY-MM-DD` strings.
- Storage remains schema version 1 TSV-compatible with the Cangjie implementation.
- The first run seeds default parent categories but creates no example expense.
- The default data path is `%APPDATA%\\Suishouji\\ledger.tsv`; `MINIPROJECT_DATA_DIR` overrides it in tests.
- A filled note is the only list content; an empty note falls back to the parent category name.
- Delete requires confirmation; failed writes must not report success.
- The repository must retain the Cangjie project, tests, README, and meaningful commit history.

## Review Focus

- A malformed or truncated TSV file must show an error and preserve the file rather than silently resetting the ledger; test in `windows_app/test_storage.py`.
- A date, amount, duplicate category, or budget validation error must leave the previous in-memory state unchanged; test in `windows_app/test_domain.py`.
- Editing a record across dates or months must update both old and new summaries; test in `windows_app/test_domain.py`.
- A note containing tabs, newlines, backslashes, or only whitespace must round-trip and follow the display rule; test in `windows_app/test_storage.py` and `windows_app/test_domain.py`.
- A clean first run must use an empty expense list while retaining the four default categories; test in `windows_app/test_storage.py`.

### Task 1: Windows domain and storage adapter

**Files:**
- Create: `windows_app/__init__.py`
- Create: `windows_app/ledger_domain.py`
- Create: `windows_app/ledger_storage.py`
- Create: `windows_app/test_domain.py`
- Create: `windows_app/test_storage.py`
- Modify: `.gitignore`

**Interfaces:**
- `ledger_domain.LedgerState`, `Category`, `Expense`, `MonthlyBudget` dataclasses.
- `ledger_domain.LedgerService` methods `seed_defaults`, `add_category`, `rename_category`, `add_expense`, `update_expense`, `delete_expense`, `set_budget`, `summarize_date`, `summarize_month`, and `budget_status`.
- `ledger_domain.expense_display_text(note, category_name) -> str`.
- `ledger_storage.serialize_state(state) -> str`, `deserialize_state(raw) -> LedgerState`, `load_state(path) -> LedgerState`, `save_state(path, state) -> None`, and `default_data_path() -> Path`.

- [ ] Write failing tests for valid/invalid amounts and dates, duplicate categories, exact-cent summaries, budget overrun, note display, TSV round-trip, malformed records, and empty first-run defaults.
- [ ] Run `python -m unittest windows_app.test_domain windows_app.test_storage -v` and observe failures because the modules do not exist.
- [ ] Implement the domain and storage adapter with atomic replacement and the schema version 1 record format.
- [ ] Run the focused Python tests and confirm all normal, boundary, and error cases pass.
- [ ] Commit `feat: add windows ledger domain adapter`.

### Task 2: PySide6 shell and details flow

**Files:**
- Create: `windows_app/main.py`
- Create: `windows_app/test_ui.py`
- Create: `windows_app/style.qss`
- Create: `requirements-windows.txt`

**Interfaces:**
- `main.LedgerWindow(service, store)` accepts an injected service and storage adapter.
- `main.main()` resolves the user data path, loads state, and starts the Qt event loop.
- UI signals call service methods, save only after successful validation, and refresh the current page from state.

- [ ] Write a Qt offscreen smoke test for window construction, four navigation actions, empty-state rendering, and the central “记一笔” action.
- [ ] Run the UI test with `QT_QPA_PLATFORM=offscreen`; it must fail clearly when PySide6/UI classes are absent.
- [ ] Add the dependency declaration and implement the shell, palette, typography, sidebar, summary cards, date/month filters, aligned expense table, empty state, category picker, and add/edit expense dialog.
- [ ] Verify the detail flow in the offscreen test: filled notes show only the note, blank notes show the category, and save failures keep the dialog open.
- [ ] Run the domain/storage suite plus the Qt smoke suite and inspect a local screenshot when PySide6 is available.
- [ ] Commit `feat: add windows pyside6 detail client`.

### Task 3: Statistics, budget, categories, and import flow

**Files:**
- Modify: `windows_app/main.py`
- Modify: `windows_app/ledger_domain.py`
- Create: `windows_app/test_acceptance.py`

**Interfaces:**
- Statistics page consumes `summarize_date` and `summarize_month` and displays totals that sum to the selected range.
- Budget page consumes `set_budget` and `budget_status` and caps the progress bar at 100% while showing the true overrun text.
- Categories page adds and renames parent/child categories and refreshes the picker immediately.
- Import action reads an existing schema version 1 TSV selected by the user and writes it to the Windows data path only after a successful parse.

- [ ] Write acceptance tests for statistics, budget states, category add/rename, import success, import cancellation, and import rejection without data loss.
- [ ] Run the acceptance tests before implementation and confirm the missing UI/service behavior fails.
- [ ] Implement the remaining pages, dialogs, import action, confirmation prompts, and refresh routing.
- [ ] Run the full Python test suite and exercise the PRD acceptance path with an isolated temporary data directory.
- [ ] Commit `feat: complete windows ledger workflows`.

### Task 4: Windows packaging and delivery documentation

**Files:**
- Create: `packaging/windows.spec`
- Create: `.github/workflows/windows-build.yml`
- Modify: `README.md`
- Modify: `dev.sh`
- Modify: `.gitignore`

**Interfaces:**
- `windows-build.yml` installs Python dependencies, runs Python tests, runs Cangjie reference checks where available, builds the PyInstaller executable on `windows-latest`, and uploads `suishouji-windows-x64.zip`.
- README documents Windows prerequisites for source development, the packaged artifact path, data location, import behavior, test commands, and the Ubuntu/Cangjie reference role.
- `dev.sh` keeps existing Ubuntu commands and adds a clearly labeled Python/Windows-client test command without pretending to build Windows locally.

- [ ] Write a packaging smoke check that verifies the spec names the entry point, application name, and output artifact.
- [ ] Run the check before adding the workflow/spec and observe the expected missing-file failure.
- [ ] Implement the PyInstaller spec, workflow, README, and local command aliases.
- [ ] Run all local Python/Cangjie checks and validate the workflow YAML and spec structure.
- [ ] Commit `build: package windows desktop client`.

### Task 5: Final verification and GitHub-ready delivery

**Files:**
- Modify: `docs/verification-v1.md`
- Modify: `README.md`

- [ ] Run the complete local suite, an isolated persistence restart check, and an offscreen UI smoke check when dependencies are available.
- [ ] Review the Windows acceptance checklist against PRD scenarios A01-A18 that apply to desktop use.
- [ ] Record the limitations that only GitHub Actions can verify: Windows executable startup and artifact download.
- [ ] Commit `docs: document windows v1 verification`.
- [ ] Confirm `git status`, commit history, and the GitHub Actions artifact path; push only after the user's configured credentials are available.
