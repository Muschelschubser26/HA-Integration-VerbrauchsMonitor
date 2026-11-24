# Changelog

Alle relevanten Änderungen an freigegebenen Versionen des VerbrauchsMonitors werden hier dokumentiert.

Die öffentliche Änderungshistorie beginnt mit der ersten freigegebenen Version.

## [Unreleased]

### Added

- Lokale SQLite-Datenhaltung mit Hauptdatenbank unter `/config/verbrauchsmonitor.db` und konsistenter Einzel-Backupdatenbank unter `/config/verbrauchsmonitor-backup.db`.
- Einmalige, verlustfreie Übernahme des bisherigen JSON-Datenbestands beim ersten Start mit SQLite.

### Changed

- Tarifanzeigen für Arbeits- und Einspeisetarife auf zwei Nachkommastellen begrenzt; interne Tarifpräzision und Berechnungen bleiben unverändert.
- Persistente Fachdaten werden statt im bisherigen JSON-Speicher in SQLite-Transaktionen gespeichert; JSON bleibt Import-/Exportformat.

### Fixed
