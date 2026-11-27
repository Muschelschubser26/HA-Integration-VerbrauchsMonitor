# Testbericht R140

Stand: 26.11.2026

## Änderungen
- Dynamische Monatsauswahl mit ausgeschriebenen Monatsnamen und Jahreszahl.
- Anzeige des aktuellen Abschlags und der nächsten vorgemerkten Änderung.
- Sichtbare Speicherbestätigung nach dem Speichern einer Abschlagsänderung.
- Backendseitige Gruppierung fälliger Monatsabschläge nach effektivem Betrag innerhalb des aktiven Abrechnungszeitraums.
- Getrennte Darstellung vorgemerkter/fälliger Abschläge und nachgewiesener Zahlungen.
- Automatische Sollbeträge werden nicht als tatsächlich geleistete Zahlung behandelt.
- Regressionstests für Jahreswechsel, Wirksamkeitswechsel, Periodenende, Nullbetrag und explizite Zahlungsbuchungen.

## Automatisierte Prüfungen
- Pytest: **483 bestanden**.
- Python-Syntax/Bytecode-Kompilierung (`compileall`): **bestanden**.
- JavaScript-Syntax (`node --check`): **bestanden**.
- JSON-Dateien: **4 geprüft, keine Fehler**.
- Deutsche Quelldatei `strings.json` und deutsche Übersetzung `translations/de.json`: **identisch**.
- Schlüsselstruktur Deutsch/Englisch: **identisch**.
- ZIP-Integrität (`testzip`) und Archivstruktur: **bestanden**; vollständiges Projekt mit `ha-verbrauchsmonitor/` als Wurzelordner und Integration unter `custom_components/verbrauchsmonitor/` enthalten.

## Nicht durchgeführte Prüfungen
- Kein vollständiger Laufzeittest in einer realen Home-Assistant-Instanz.
- Config-Flow-Darstellung, Entity-Registry-Verhalten, Recorder-Verlauf und Dashboard-Layout müssen nach Installation in Home Assistant geprüft werden.
