# Changelog

All notable changes to this project will be documented in this file.

This project follows the spirit of Keep a Changelog and uses simple sections such as Added, Changed, Fixed, and Security.

## Unreleased

### Changed

## v0.1.1-alpha - 2026-06-25

### Added

- Add archived release notes for `v0.1.1-alpha`.
- Add GitHub Actions CI for the Python test suite.
- Add a project status document summarizing governance settings, CI, branch rules, open items, and maintainer notes.
- Add repository governance files for security reporting, pull request review, ownership, dependency updates, changelog tracking, and community conduct.
- Add maintainer notes for the `master` ruleset, update workflow, generated artifact checks, and GitHub comment encoding.
- Add PowerShell regression coverage for the one-click patch generation path.

### Changed

- Localize GitHub issue templates to avoid confusing browser-translated labels.
- Clarify the recommended download path and why generated `data.unity3d` files can be much larger than the official bundle.
- Update `v0.1.1-alpha` release notes to use neutral user-facing troubleshooting guidance.
- Update project status after closing Issue #3 and merging Dependabot PR #2.
- Clarify the translation update cadence, Traditional Chinese plan, and generated bundle scope in user-facing documentation.
- Allow the normal patch generation script to continue when the current game version no longer contains some translated terms, with a clear warning before and during generation.
- Document that newly added game text may remain untranslated until the translation table is updated.

### Fixed

- Add the missing `needs-triage` and `dependencies` GitHub labels used by issue templates and Dependabot.
- Update the development test dependency to `pytest==9.1.1`.
- Prevent Python build output from polluting the PowerShell function return value used by the one-click generation script.
