# Testbericht – Dev R169

## Automatisierte Tests

- Gesamt: 578 Tests bestanden.
- Datenbank: SQLite-Schema-1-Migration, Vor-Migrationsbackup, Backfill, Snapshot-Kompatibilität, Tabellen-Lesepriorität, Config-Entry-Projektion, Fremdschlüsselprüfung und Erhalt nicht auflösbarer Original-Payloads.
- Messwerte: numerische Werte, Nullwerte, unbekannte/verfügbare Zustände, Text, negative Werte, NaN, positive/negative Unendlichkeit, boolesche Werte, monotone Steigerung, Gleichstand und Rückgang.
- Prognose: bestehende Regressionen sowie das eigenständige Kalender-Jahreszeitenmodell, fehlende Saisonwerte und anteilige Projektion des aktuellen Tages.
- UI: geänderte Zahlungsbeschriftung in Deutsch und Englisch.

## Weitere statische Prüfungen

- Python-Syntax: geprüft.
- JavaScript-Syntax: geprüft.
- JSON-Dateien: geprüft.
- Deutsche und englische Übersetzungsstrukturen: geprüft.
- ZIP-Inhaltsstruktur: vollständige Integration einschließlich Dokumentation und Tests.

## Nicht durch automatisierte Tests ersetzbar

Ein vollständiger Home-Assistant-Laufzeittest wurde nicht durchgeführt. Insbesondere müssen auf dem Zielsystem Setup/Reload, Config-Entry-Migration, Recorder-Wiederherstellung, echte Zählerwechsel, Mitternachts-/Wochen-/Monats-/Jahreswechsel und die visuelle Kartenanzeige geprüft werden.

## Migrationsschutz

Die Schema-1-Datenbank wird vor der Schemaerweiterung als `verbrauchsmonitor-pre-r169-backup.db` gesichert. Diese Sicherung wird nicht automatisch überschrieben. Die bestehende `vm_state`-Payload bleibt als Kompatibilitäts- und Exportbasis erhalten. Die Migration löscht keine Periodenwerte oder Perioden-Stores.
