# Testbericht – Beta R170

## Änderungen

- Alle Recorder-Abfragen für Langzeitstatistiken und detaillierte Historie werden über `get_instance(hass).async_add_executor_job()` ausgeführt.
- Die CPU-intensive Prognoseberechnung bleibt im allgemeinen Executor, da sie keine Recorder-Datenbankoperation ist.
- Fehlende Quellzustände sowie `unknown` und `unavailable` werden vor der Messwertvalidierung ignoriert. Dadurch werden beim Start/Reload weder Referenzen verändert noch Warnungen für erwartbare temporäre Zustände ausgegeben.
- Numerisch ungültige Werte und unzulässige Zählerstands-Rückgänge werden weiterhin strikt zurückgewiesen.

## Automatisierte Prüfungen

- Vollständige pytest-Suite: **584 bestanden** (2,73 Sekunden).
- Neue Regressionstests prüfen, dass Recorder-Statistik- und Historienabfragen den Recorder-Executor verwenden.
- Neue Regressionstests prüfen, dass beide Quellzustands-Listener transiente Zustände vor der Validierung abfangen.
- Bestehende Messwertvalidierungs-, Zählerwechsel-, Periodenwechsel-, Datenbank- und Prognosetests werden mit ausgeführt.
- Python-Syntax, JSON-Dateien, Übersetzungsstruktur und ZIP-Integrität werden separat geprüft.

## Laufzeittest

Ein vollständiger Home-Assistant-Laufzeittest ist in dieser Umgebung nicht möglich. Auf dem Zielsystem sind insbesondere Integration-Setup/Reload, Recorder-Abfragen nach Neustart, Start mit `unknown`/`unavailable` Quellzuständen sowie die Forecast-Historienaktualisierung zu prüfen.
