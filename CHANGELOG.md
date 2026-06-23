# Changelog

All notable changes to this project will be documented in this file.

This project follows the spirit of Keep a Changelog and uses simple sections such as Added, Changed, Fixed, and Security.

## Unreleased

### Added

- Add repository governance files for security reporting, pull request review, ownership, dependency updates, changelog tracking, and community conduct.
- Add maintainer notes for the `master` ruleset, update workflow, generated artifact checks, and GitHub comment encoding.
- Add PowerShell regression coverage for the one-click patch generation path.

### Changed

- Allow the normal patch generation script to continue when the current game version no longer contains some translated terms, with a clear warning before and during generation.
- Document that newly added game text may remain untranslated until the translation table is updated.

### Fixed

- Prevent Python build output from polluting the PowerShell function return value used by the one-click generation script.
