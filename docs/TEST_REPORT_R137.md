# Testbericht – VerbrauchsMonitor Beta R137

## Änderungsumfang
- Die Watt-Anzeige der Zählerkarte vergleicht bei vorhandener positiver Einspeisung den Betrag der Einspeiseleistung mit der Verbrauchsleistung.
- Einspeisung größer Verbrauch: ausschließlich der Watt-Text wird grün.
- Einspeisung kleiner Verbrauch: ausschließlich der Watt-Text wird rot.
- Gleiche Werte: Watt-Text bleibt grau.
- Ohne positive Einspeisung bleibt die bisherige graue Anzeige erhalten.
- Es werden keine Icons oder zusätzlichen Texte ergänzt. Messwerte, Backend und Abrechnungsberechnungen bleiben unverändert.

## Automatisierte Prüfungen
- Pytest: 474 bestanden.
- Python-Kompilierung: erfolgreich.
- JavaScript-Syntaxprüfung (`node --check`): erfolgreich.
- JSON-Validierung: erfolgreich.
- Deutsche und englische Übersetzungsstruktur: identisch.

## Nicht durchgeführte Prüfungen
- Kein vollständiger Home-Assistant-Laufzeittest.
- Keine visuelle Prüfung in einem laufenden Home-Assistant-Browser. Farben und tatsächliche Darstellung sind nach Installation zu kontrollieren.
