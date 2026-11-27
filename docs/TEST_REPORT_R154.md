# Testbericht Beta R154

## Änderungen
- Fortschritt der Zuverlässigkeitsermittlung als separates Attribut ergänzt.
- Anzeige `(xx %)` zwischen „wird ermittelt“ und dem Spinner.
- Berechnungsphasen melden 5 %, 20 %, 65 %, 90 % und 100 %; diese Werte stehen ausschließlich für den technischen Ablauf, nicht für Prognosezuverlässigkeit.
- Fortschritt wird monoton gehalten; neue Zustandsänderungen setzen ihn nicht zurück. Während einer Aktualisierung signalisiert der Spinner weiterhin die laufende Berechnung.
- Keine neuen Home-Assistant-Entitäten.

## Automatisierte Prüfungen
- Python- und JavaScript-Syntax: erfolgreich.
- JSON-Dateien: werden im Release-Prüfschritt validiert.
- Regressionstests: siehe unten.

## Laufzeitgrenzen
- Kein echter Home-Assistant-Frontend-/Browser-Test in einer laufenden Instanz durchgeführt.
- Recorder-, Neustart- und Updateverhalten muss weiterhin im Zielsystem geprüft werden.
- Die Prozentanzeige beschreibt abgeschlossene Berechnungsphasen, nicht eine zeitlich genaue Restlaufzeitschätzung.
