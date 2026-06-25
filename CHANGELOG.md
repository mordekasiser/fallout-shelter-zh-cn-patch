# Changelog

All notable changes to this project will be documented in this file.

This project follows the spirit of Keep a Changelog and uses simple sections such as Added, Changed, Fixed, and Security.

## Unreleased

### Changed

- Localize GitHub issue templates to avoid confusing browser-translated labels.

### Fixed

- Add the missing `needs-triage` and `dependencies` GitHub labels used by issue templates and Dependabot.

## v0.1.1-alpha - 2026-06-25

### Added

- Add archived release notes for `v0.1.1-alpha`.
- Add GitHub Actions CI for the Python test suite.
- Add a project status document summarizing governance settings, CI, branch rules, open items, and maintainer notes.
- Add repository governance files for security reporting, pull request review, ownership, dependency updates, changelog tracking, and community conduct.
- Add maintainer notes for the `master` ruleset, update workflow, generated artifact checks, and GitHub comment encoding.
- Add PowerShell regression coverage for the one-click patch generation path.

### Changed

- Allow the normal patch generation script to continue when the current game version no longer contains some translated terms, with a clear warning before and during generation.
- Document that newly added game text may remain untranslated until the translation table is updated.

### Fixed

- Prevent Python build output from polluting the PowerShell function return value used by the one-click generation script.
