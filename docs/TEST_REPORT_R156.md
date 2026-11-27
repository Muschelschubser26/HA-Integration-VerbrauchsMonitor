# Testbericht Beta R156

## Fehlerkorrektur

Die bisherige Zuverlässigkeitsauflösung verwendete ausschließlich mindestens 24 gespeicherte stündliche Prognose-Ist-Vergleiche. Eine vorhandene, ausreichend lange Recorder-Historie wurde für die initiale Zuverlässigkeitsanzeige nicht verwendet. Dadurch konnte trotz umfangreicher Messhistorie „keine Bewertungsgrundlage“ erscheinen.

R156 verwendet die vorhandene Recorder-Historienqualität als initiale Bewertungsgrundlage. Sie berücksichtigt ausschließlich bereits verfügbare Eigenschaften der Historie (Dauer, Abdeckung, Kontinuität, Plausibilität und Prognosemethode) und wird ausdrücklich nicht als gemessene Prognosegenauigkeit bezeichnet. Sobald mindestens 24 gültige stündliche Prognose-Ist-Vergleiche vorliegen, haben diese Vorrang.

## Prüfungen

- Regressionstest: nutzbare Recorder-Historie erzeugt bereits ohne 24 Forecast-Ist-Paare eine initiale Bewertung.
- Regressionstest: 24 gültige Forecast-Ist-Paare haben Vorrang vor der initialen Historienbewertung.
- Bestehende Tests für fehlende Historie, keine künstlichen Werte, zeitliche Begrenzung und 95-%-Obergrenze.
- Python-Syntax, JSON, Übersetzungsdateien und ZIP-Integrität.

Ein vollständiger Home-Assistant-Laufzeittest mit der produktiven Recorder-Datenbank ist nicht Bestandteil dieser automatisierten Prüfung.
