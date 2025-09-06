# AGENTS.md

This repository uses CLAUDE.md files as the authoritative agent instructions. This file exists only so agent tooling (e.g., Codex CLI) can discover that documentation.

- Do not add or change guidance here.
- Follow the instructions in these files instead:
  - `./CLAUDE.md` (root)
  - `./backend/CLAUDE.md`
  - `./agent/CLAUDE.md`
  - `./frontend/CLAUDE.md`

Scope and precedence: This file applies to the entire repo; AGENTS.md files in subdirectories take precedence for their subtrees.

