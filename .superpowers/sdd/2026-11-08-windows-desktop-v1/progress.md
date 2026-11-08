# SDD ledger — plan: docs/superpowers/plans/2026-11-08-windows-desktop-v1.md

## Setup

- Ruling: Work in current checkout — user asked to continue in the current repository and wants the resulting commits on GitHub; creating another worktree would hide the files they are inspecting.
- Pre-flight: Task 1 produces domain/storage interfaces consumed by Tasks 2 and 3; Task 2 UI consumes injected service/storage and Task 3 extends the same service; no naming conflict found.
- Decision recorded: Windows first run starts with an empty ledger and offers an explicit import action for the old Ubuntu TSV file.
- Decision recorded: GitHub Actions publishes a zip containing the Windows executable; no installer or code-signing requirement for v1.

## Progress

- [x] Task 1 — Windows domain/storage adapter (tests and implementation complete)
- [ ] Task 2 — PySide6 shell and details page
- [ ] Task 3 — Stats, budget, categories, and import workflows
- [ ] Task 4 — Windows packaging and GitHub Actions
- [ ] Task 5 — Final verification and delivery notes
Task 1: complete (commits 8717737..8717737, tests: python3 -m unittest windows_app.test_domain windows_app.test_storage -v → OK)
