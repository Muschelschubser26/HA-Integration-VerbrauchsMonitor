# Testbericht Beta R152

## Änderungsumfang
- Die monatliche Abschlagsempfehlung wird nicht mehr von der Verfügbarkeit einer Zuverlässigkeits-Prozentzahl abhängig gemacht. Ein gültiger Empfehlungsbetrag bleibt sichtbar, auch wenn die Zuverlässigkeit noch nicht bewertet werden kann.
- Es wird kein künstlicher Mindestwert für die Zuverlässigkeit erzeugt; insbesondere wird keine 1-%-Untergrenze eingeführt.
- Der Lernverlauf bleibt je Config-Entry, logischem Zähler und Richtung getrennt und dauerhaft in Home Assistants `Store` gespeichert.
- Zusätzlich wird eine zweite persistente Sicherung geführt. Fehlt die Hauptspeicherung oder enthält sie keine Lernhistorie, wird eine vorhandene Sicherung eingelesen und die Hauptspeicherung wiederhergestellt.
- Gespeicherte Lernzustände werden strukturell geprüft. Gültige Prognose- und Bewertungsdatensätze sowie unbekannte Metadaten bleiben erhalten; einzelne fehlerhafte Datensätze führen nicht zum Verwerfen der gesamten Historie.
- Es werden keine neuen Home-Assistant-Entitäten angelegt.

## Automatisierte Prüfungen
- Pytest: **515 Tests bestanden**.
- Python-Bytecode-Kompilierung: erfolgreich.
- JavaScript-Syntaxprüfung (`node --check`): erfolgreich.
- JSON-Syntaxprüfung: alle JSON-Dateien gültig.
- Deutsche und englische Übersetzungsstrukturen: vollständig synchron.
- Release-Metadaten: Beta R152 konsistent.
- Regressionen: Empfehlung unabhängig von Zuverlässigkeitsverfügbarkeit, keine künstliche Zuverlässigkeits-Untergrenze, stabile Speicherkennung, Wiederherstellung aus Sicherung, Validierung einzelner Datensätze.
- ZIP-Integrität: wird nach Erstellung geprüft.

## Nicht in dieser Umgebung prüfbar
- Kein echter Home-Assistant-Neustart mit R151/R152 und vorhandenen `.storage`-Lernverlaufsdateien.
- Kein absichtliches Beschädigen/Entfernen der Hauptspeicherung im laufenden Home Assistant, um den Restore aus der Sicherung praktisch zu beobachten.
- Keine Prüfung mit den tatsächlichen Recorder-Daten und echten Zählerverläufen.
- Keine Langzeitbeobachtung über mehrere Monate/Jahre; die empirische Verbesserung muss im laufenden Betrieb nachgewiesen werden.
- Der unabhängige Abgleich historischer Zuverlässigkeits-Prozentwerte mit späterer Prognosequalität und der Vergleich finanzieller Prognosen mit abgeschlossenen Abrechnungen bleiben offene Entwicklungsarbeiten.

Automatisierte Tests ersetzen keinen vollständigen Home-Assistant-Laufzeittest.
