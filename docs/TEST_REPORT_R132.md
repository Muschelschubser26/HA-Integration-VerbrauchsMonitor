# Testbericht – VerbrauchsMonitor Beta R132

## Umgesetzte Änderungen

- Zufallsbasierte Zuverlässigkeits-Initialisierung entfernt.
- Initiale Ermittlung auf maximal 15 Minuten begrenzt; Aktualisierung des Status alle fünf Minuten.
- Nach Ablauf der initialen Ermittlung wird immer ein numerischer Wert aus der verfügbaren Datenbasis angezeigt. Der Wert berücksichtigt Historienlänge, Messabdeckung, Datenqualität, Stichprobenumfang und Vollständigkeit verfügbarer Kontextdaten je Zähler und Abrechnungsrichtung.
- Sobald mindestens fünf abgeschlossene stündliche Prognosevergleiche vorliegen, fließt deren gemessene Genauigkeit mit wachsendem Gewicht in die Bewertung ein. Dadurch wird der Wechsel vom Datenbasiswert zur gemessenen Prognosequalität schrittweise statt abrupt vollzogen.
- „Wird ermittelt“ erhält einen rotierenden Ladekreis; reduzierte Bewegungseinstellungen werden berücksichtigt.
- Einspeiseleistung wird ausschließlich in der Kartenanzeige als Absolutwert dargestellt.
- Einspeisungs-Zahlungssumme erhält die Beschriftung „Gesamt erhaltene Zahlungen:“; Verbrauch bleibt bei „Gesamt geleistete Zahlungen:“.
- Prognoseüberschrift mit Abrechnungsdatum bleibt soweit möglich einzeilig und passt die Schriftgröße responsiv an.

## Automatisierte Prüfungen

- Python-Bytecode-/Syntaxprüfung: bestanden.
- JavaScript-Syntaxprüfung (`node --check`): bestanden.
- Unit- und Regressionstests: **450 bestanden**.
- JSON-Dateien: separat zu validieren; Übersetzungsdateien DE/EN werden im Paket auf JSON-Syntax und Schlüsselparität geprüft.
- ZIP-Integrität: separat geprüft.

## Grenzen der Prüfung

- Kein vollständiger Home-Assistant-Laufzeittest mit Recorder-Datenbank und realen Zählerentitäten möglich.
- Keine Browserprüfung in einer laufenden Home-Assistant-Instanz möglich. Die tatsächliche Kartenbreite hängt weiterhin vom Lovelace-Layout und der verfügbaren Spaltenbreite ab; die Überschrift wird nur innerhalb des zugewiesenen Kartenbereichs kompakter dargestellt.
- Die Monatsabschlagsanzeige mit 0,00 € aus dem Screenshot ist mit diesem Paket nicht abschließend korrigiert. Dafür muss eindeutig geklärt werden, ob Verbrauch oder Einspeisung betroffen ist und ob die 0-Werte als explizite Monatsbuchungen oder als fehlende Monatswerte vorliegen. Bewusst gespeicherte 0,00 € dürfen nicht überschrieben werden.
- Die Zuverlässigkeitszahl ist bis zum Vorliegen ausreichender Prognosevergleiche ausdrücklich eine Bewertung der verfügbaren Datenbasis, nicht bereits eine statistisch gemessene Prognosegenauigkeit. Die Kartenoberfläche zeigt beide Fälle numerisch; die Attribute `forecast_reliability_basis` unterscheiden die Grundlage.
