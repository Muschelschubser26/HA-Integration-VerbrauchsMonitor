# Changelog

All relevant changes to released versions of VerbrauchsMonitor are documented here.

The public changelog starts with the first released version.

## [Unreleased]

### Added

- Local SQLite data storage with the main database at `/config/verbrauchsmonitor.db` and a consistent single backup database at `/config/verbrauchsmonitor-backup.db`.
- One-time, lossless migration of the existing JSON data during the first startup with SQLite.

### Changed

- Displayed energy and feed-in tariffs are limited to two decimal places; internal tariff precision and calculations remain unchanged.
- Persistent business data is stored in SQLite transactions instead of the previous JSON storage; JSON remains the import/export format.

### Fixed
