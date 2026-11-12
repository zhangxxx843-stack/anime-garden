# Top Music Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-functional, accessible “add background music” popover beside the existing top music controls.

**Architecture:** Extend the existing `shell()` header markup and bind the new controls alongside the current music controller. Keep all state temporary in the rendered DOM and use the existing toast and button-sound systems.

**Tech Stack:** Vanilla JavaScript, CSS, Node test runner

**Spec:** `docs/superpowers/specs/2026-11-12-top-music-entry-design.md`

## Global Constraints

- Do not implement file reading, upload, persistence, or playback.
- Preserve the current header navigation, background player, button animation, and sound.
- Keep the warm manga-sticker visual language and responsive behavior.

## Review Focus

- Re-rendering after hash navigation must leave exactly one working popover trigger.
- Clicking outside or pressing Escape should close the panel without stopping the music.
- A filename containing markup must be displayed as text, not injected as HTML.
- The control must remain keyboard accessible and expose expanded state.
- Narrow layouts must keep the panel inside the viewport.

---

### Task 1: Top Music Entry and Popover

**Files:**
- Modify: `public/app.js`
- Modify: `public/styles.css`
- Test: `tests/server.test.mjs`

**Interfaces:**
- Consumes: existing `shell()`, `toast(message)`, `.anime-action`, and `.music-control`
- Produces: `#music-add`, `#music-add-panel`, `#music-file`, and `#music-add-submit` DOM controls

- [x] **Step 1: Write the failing test**

Add assertions that the header renders the four control IDs, marks the trigger with `aria-expanded`, displays the selected filename through `textContent`, handles Escape/outside click, and includes responsive popover styles.

- [x] **Step 2: Run test to verify it fails**

Run: `node --test tests/*.test.mjs`

Expected: FAIL because the music-add controls do not exist.

- [x] **Step 3: Implement the controls in `public/app.js`**

Extend `shell()` markup, bind open/close/file-change/submit handlers after header render, and reuse `toast('功能开发中')`. Never consume the file bytes.

- [x] **Step 4: Implement the popover presentation in `public/styles.css`**

Anchor the panel to the compact music control group, use the established warm sticker tokens, and constrain the panel within narrow viewports.

- [x] **Step 5: Run syntax and regression tests**

Run: `node --check public/app.js && node --check server.mjs && node --test tests/*.test.mjs`

Expected: all checks PASS.

- [x] **Step 6: Restart and inspect the local preview**

Verify `http://127.0.0.1:3210/#home` preserves playback controls and opens/closes the new panel correctly.
