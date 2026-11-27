# Testbericht – Beta R150

## Änderungen
- Menüpunkt und Formularüberschrift heißen „Prognose & Zuverlässigkeit“.
- Fünf optionale Sensorentitäten für Umgebungsdaten sind konfigurierbar.
- Die Auswahl wird in `ConfigEntry.options` gespeichert und an alle Meter-Prognosekontexte weitergereicht.
- Gültige und aktuelle Umgebungswerte fließen als Datenqualitätsfaktoren in Modul A ein.
- Nicht konfigurierte, unbekannte, nicht numerische oder unplausible Werte werden ausgelassen.
- Änderungen der Quell- und Umgebungsentitäten lösen eine Neuberechnung aus.
- DE/EN-Übersetzungen wurden synchronisiert.

## Automatisierte Prüfungen
- pytest: **507 bestanden**
- Python compileall: bestanden
- JavaScript `node --check`: bestanden
- JSON-Dateien: 4 geprüft, alle gültig
- Übersetzungsstruktur: 194 Schlüsselpfade DE/EN synchron; `strings.json` entspricht DE
- ZIP-Integrität: wird nach Archivierung geprüft

## Testabdeckung der neuen Funktionen
- Konfigurationsfelder und optionale Speicherung
- Sensorwerte für Temperatur, Helligkeit, Windrichtung, Tagesniederschlag und Luftfeuchtigkeit
- Veraltete und unplausible Werte
- Keine konfigurierten optionalen Sensoren
- Neuberechnung bei Änderungen der optionalen Entitäten
- Übersetzungen Deutsch/Englisch

## Einschränkungen
- Ein Home-Assistant-Laufzeittest ist nicht durchführbar in dieser isolierten Testumgebung.
- Die Umgebungswerte werden in R150 als Datenqualitäts- und Kontextfaktoren in die Zuverlässigkeitsbewertung aufgenommen. Sie sind keine eigenständige PV-Leistungs- oder Wetterprognose.
- Die native Home-Assistant-Config-Flow-Oberfläche bietet keine verlässliche Möglichkeit, eine frei positionierte horizontale Trennlinie mitten zwischen Schemafeldern zu erzwingen. Die fünf optionalen Felder stehen in der Formularreihenfolge direkt nach der Prognoseauswahl; die Formularbeschreibung weist auf den zusätzlichen Bereich hin.
