# Windows Desktop V1 Design

## Intent

Turn the current Ubuntu-only prototype into a usable Windows desktop version of “随手记”. The Windows build must open directly, keep data offline, present the PRD flows clearly, and be buildable from GitHub without requiring a Cangjie SDK on the user's computer.

## Goals

- Deliver a Windows 10/11 x64 desktop client with a polished, readable interface.
- Cover the PRD flows F01-F08: expense entry, two-level category management, date/month queries, detail/edit/delete, daily and monthly summaries, monthly budgets, and local persistence.
- Keep the existing Cangjie project, protocol, tests, and TSV schema as the course reference implementation.
- Add a Windows build path that produces a portable `.exe` or zipped application from GitHub Actions.
- Make the Windows client start with an empty ledger on a new machine and use a stable per-user data path.

## Non-goals

- Android and iOS clients in this delivery.
- Login, registration, cloud sync, income, transfers, or category deletion.
- Requiring the user to install Cangjie, Python, or a development environment to run the packaged Windows client.
- Treating the existing Ubuntu Tk screen as the final product UI.

## Constraints

- Cangjie 1.0.5 remains in the repository and its model, service, storage, protocol, and tests remain runnable in the course environment.
- The Windows client must be independently runnable because the current Linux Cangjie executable cannot be shipped as a Windows backend.
- Amounts remain integer cents, dates remain local `YYYY-MM-DD`, and storage remains compatible with schema version 1 TSV records.
- The user requested GitHub delivery; the repository must contain source, build instructions, and a Windows build workflow.
- The current Ubuntu environment has no PySide6, Windows SDK, or Windows Cangjie toolchain, so local verification covers Python logic, UI construction where dependencies are available, and repository checks. Windows packaging is verified by the GitHub Actions runner.

## Approaches considered

### PySide6 Windows client — selected

Build a Qt desktop UI in Python and put the Windows business/storage adapter in focused Python modules. The adapter reads and writes the same versioned TSV format as the Cangjie core and exposes the same validation rules. PyInstaller packages the client and PySide6 into a Windows executable. This gives the project a real Windows UI, avoids a Cangjie runtime dependency for end users, and lets GitHub Actions build on `windows-latest`.

### Continue extending Tk

This would keep the existing GUI and reduce short-term code changes, but it would preserve the visual limitations that prompted the redesign and still require a separate Windows backend and packaging path. It does not meet the requested product quality.

### Cross-compile and embed Cangjie on Windows

This would keep one business implementation, but the current environment has no Windows Cangjie SDK or verified embedding/packaging ABI. It would make the Windows deliverable depend on an unverified toolchain and does not solve the UI quality problem by itself.

## Product structure

The Windows client opens to a four-page shell with a left navigation rail and one prominent “记一笔” action:

- **明细**: date/day or month filter, total, count, budget summary, and an aligned expense table.
- **统计**: total, count, category totals, and percentages for the selected month.
- **预算**: selected month, budget input, spent amount, remaining or over-budget state, and capped progress bar.
- **分类**: parent categories, child categories, add and rename actions, and the selected category context.

The expense flow is a modal sequence: choose a top-level category, enter amount/date/optional note, save, and return to the matching detail view. An empty note displays the category name in list rows; a filled note displays only the note. Selecting a row shows the full detail card with edit and delete actions. Delete requires confirmation.

## Windows storage and runtime

- Default data path: `%APPDATA%\\Suishouji\\ledger.tsv`.
- Tests may override the path with `MINIPROJECT_DATA_DIR`.
- Writes use a temporary file followed by replacement, preserving the previous file when validation or writing fails.
- A first run seeds the four default parent categories without creating example expenses.
- The packaged app uses a bundled Python runtime from PyInstaller and does not invoke `dev.sh` or a Linux executable.

## Code boundaries

- `windows_app/ledger_domain.py`: Python dataclasses, amount/date/category/expense/budget validation, summaries, and display rules.
- `windows_app/ledger_storage.py`: schema version 1 TSV encode/decode, per-user path selection, atomic writes, and corruption errors.
- `windows_app/main.py`: PySide6 window, pages, dialogs, state refresh, and user feedback.
- `windows_app/test_*.py`: domain/storage tests and UI construction smoke tests that do not require a display when possible.
- `packaging/windows.spec`: PyInstaller configuration for the Windows executable.
- `.github/workflows/windows-build.yml`: Windows build, tests, PyInstaller packaging, and artifact upload.
- `README.md`: Windows setup, run, data location, build artifact, acceptance path, and the remaining Ubuntu/Cangjie reference role.

## Acceptance evidence

- A clean checkout can run Python tests without using the old Ubuntu backend.
- A Windows Actions job passes the domain/storage tests and creates a `.zip` containing the executable.
- Manual Windows checks cover: first launch, add with and without note, edit, delete confirmation, category add/rename, date/month filtering, statistics, budget overrun, close/reopen persistence, and data path visibility.
- The repository history records the Windows redesign, tests, packaging, and documentation as meaningful commits.
