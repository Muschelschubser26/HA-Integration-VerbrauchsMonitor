# Testbericht Beta R158

## Umfang

R158 untersucht und korrigiert drei weiterhin sichtbare Fehlerbereiche aus R155–R157:

1. Zuverlässigkeitsanzeige meldete trotz aktueller Messwerte „keine Bewertungsgrundlage“.
2. Tageswertsensoren zeigten im Gerätebereich nur „(heute)“.
3. Tageswertsensoren blieben unbekannt, wenn keine signifikanten Recorder-Zustände zur Rekonstruktion der Mitternachtsbasis verfügbar waren.

## Änderungen

- Die Zuverlässigkeit verwendet weiterhin zuerst echte, abgeschlossene Prognose-Ist-Vergleiche (mindestens 24 gültige Stundenvergleiche).
- Sind diese noch nicht vorhanden und ist die lange Recorder-Historie nicht ausreichend, wird eine separate initiale Eingangs-/Konfigurationsqualität aus tatsächlich verfügbaren Datenquellen berechnet. Sie wird ausdrücklich nicht als gemessene Prognosegenauigkeit bezeichnet.
- Fehlende optionale Wetterentitäten werden ausgelassen und nicht als negative Bewertung gewertet.
- Die zeitabhängige Obergrenze bleibt bestehen: regulär 92 %, innerhalb der letzten 24 Stunden 94 %, innerhalb der letzten Stunde höchstens 95 %.
- Bekannte automatisch erzeugte Registry-Platzhalter `(heute)`, `heute`, `(today)` und `today` werden auf die vollständigen Anzeigenamen korrigiert. Andere Namen werden nicht verändert.
- Die Tagesbasis wird zunächst aus Recorder-Zuständen rekonstruiert. Falls diese fehlen, wird eine kontrollierte Ersatzrekonstruktion aus mindestens zwei gültigen Langzeitstatistik-Summen des aktuellen Tages versucht. Eine negative oder nicht belastbare Basis wird verworfen; es wird kein Nullwert erfunden.

## Automatisierte Prüfungen

- `pytest -q`: **530 bestanden**.
- Python-Kompilierung (`compileall`): bestanden.
- JavaScript-Syntax (`node --check`): bestanden.
- JSON-Dateien: 4 gültig.
- Übersetzungspfade Deutsch/Englisch: 194/194 synchron, keine fehlenden Pfade.
- Zusätzliche Regressionstests für initiale Zuverlässigkeitsbewertung, Zeitobergrenze, Registry-Namenskorrektur und statistische Tagesbasisrekonstruktion.

## Nicht durchführbare Laufzeitprüfungen

Ein echter Home-Assistant-Laufzeittest mit der Recorder-Datenbank, der vorhandenen Entity Registry und den tatsächlichen Quellzählern war in dieser Build-Umgebung nicht möglich. Daher bleiben insbesondere die visuelle Geräteansicht, Recorder-Executor-Warnungsfreiheit, Mitternachtswechsel, Neustartwiederherstellung und Langzeitstatistiken im Zielsystem als praktische Tests offen.
