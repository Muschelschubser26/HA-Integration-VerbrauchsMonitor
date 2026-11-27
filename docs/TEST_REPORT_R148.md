# Testbericht – VerbrauchsMonitor Beta R148

## Änderungen

- `sensor.py` importiert `Store` explizit aus `homeassistant.helpers.storage`. Damit ist der im Home-Assistant-Log beobachtete `NameError` beim Anlegen des persistenten Lernspeichers behoben.
- Die Kartenbeschriftung lautet jetzt „Anteiliger Grundpreis“ statt „Anteiliger angefallener Grundpreis“. Berechnungswerte und interne Genauigkeit wurden nicht verändert.
- Regressionstest für den Modulebenen-Import und die Verwendung des Lernspeichers im Sensor-Lifecycle ergänzt.

## Automatisierte Prüfungen

- Pytest: **501 bestanden**.
- Python-Bytecode-Kompilierung für `custom_components/verbrauchsmonitor`: bestanden.
- JavaScript-Syntaxprüfung mit `node --check`: bestanden.
- JSON-Dateien: 4 gültig.
- Übersetzungsschlüssel: `strings.json`, `translations/de.json` und `translations/en.json` enthalten jeweils 189 identische Schlüsselpfade.
- ZIP-Integrität und Archivstruktur: nach Erstellung zu prüfen.

## Nicht durchgeführte Prüfungen / Grenzen

- Kein vollständiger Home-Assistant-Laufzeittest in einer gestarteten HA-Instanz.
- Der Sensor-Lifecycle mit echtem Recorder, Entity-Registry und realem `Store`-Backend konnte daher nicht end-to-end ausgeführt werden. Der gemeldete Importfehler ist durch Importkorrektur und Regressionstest adressiert, die tatsächliche Initialisierung in der Zielinstallation muss nach Installation bestätigt werden.
- Die Zuverlässigkeitsanzeige einschließlich realer Datenbewertung, animiertem Ladezustand und 15-Minuten-Grenze wurde in dieser Revision nicht fachlich neu implementiert oder als HA-Laufzeitverhalten nachgewiesen. R148 behebt den konkreten Initialisierungsabbruch durch den fehlenden `Store`-Import; daraus allein folgt noch kein Nachweis, dass Modul A/B unter den realen HA-Daten einen Prozentwert liefern.
