# Testbericht – Beta R171

## Umfang

- Anzeige des tatsächlich verwendeten SQLite-Datenbankpfads einschließlich Dateiname im Dialog „Datenbankinformationen“.
- Leerzeile zwischen Pfad und Statusblock.
- Leerzeile zwischen Buchungsanzahl und letzter Änderung.
- Keine Änderung an Datenbankzugriff, Schema, Migration, Optimierung oder gespeicherten Daten.

## Prüfungen

- Vollständige vorhandene pytest-Suite einschließlich neuem Regressionstest.
- Python-Syntaxprüfung aller Python-Dateien.
- JSON-Validierung aller JSON-Dateien.
- JavaScript-Syntaxprüfung, sofern Node.js verfügbar ist.
- ZIP-Integrität nach Erstellung und erneutes Ausführen der Tests aus dem entpackten Archiv.

Ein vollständiger Home-Assistant-Laufzeittest ist nicht Bestandteil dieser lokalen Prüfungen und muss auf dem Zielsystem erfolgen.
