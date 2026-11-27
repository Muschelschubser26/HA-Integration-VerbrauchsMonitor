# Testbericht – VerbrauchsMonitor Beta R147

## Änderungen

- Zuverlässigkeitsgewichte werden zentral mit `derive_impact_weights()` aus dem tatsächlichen Ergebnis von `calculate_forecast()` abgeleitet.
- Modul A wird mit dem prognostizierten Energiekostenwert gewichtet.
- Modul B wird mit dem prognostizierten finanziellen Gesamtwert und den tatsächlich im Prognoseergebnis enthaltenen Kontobewegungen gewichtet. Das Modul bleibt dadurch bei vorhandenen finanziellen Prognosewerten auch ohne Sonderbuchungen oder bereits gebuchte Abschläge verfügbar.
- Ein Einfluss von exakt 0,00 € erzeugt weiterhin kein Ersatzgewicht.
- Sensor und Bewertungsmodul verwenden dieselbe zentrale Gewichtungsfunktion.
- Der bestehende Frontend-Status „Zuverlässigkeit: wird ermittelt“ samt CSS-Animation bleibt bestehen. Ein verfügbarer Prozentwert hat Vorrang und wird direkt angezeigt.
- Historische Prognose-/Ist-Vergleiche bleiben getrennt und werden erst ab 24 gültigen Stundenvergleichen einbezogen.

## Automatisierte Prüfungen

- Pytest: **499 bestanden**.
- Python-Kompilierung (`compileall`): bestanden.
- JavaScript-Syntax (`node --check`): bestanden.
- JSON: 4 Dateien gültig.
- Übersetzungsstruktur: `de.json` und `en.json` jeweils 268 Schlüsselpfade, vollständig synchron.
- `strings.json` und `de.json`: 268 Schlüsselpfade, vollständig synchron.
- ZIP-Integrität und Archivstruktur: vor Auslieferung geprüft.

## Gezielte Zuverlässigkeitstests

- Tatsächliches Ergebnis von `calculate_forecast()` mit realistischen Verbrauchs-, Tarif-, Grundpreis- und Zahlungswerten erzeugt positive Euro-Einflussgewichte für A und B.
- Ohne Messhistorie wird ein reproduzierbarer numerischer Wert aus den aktuellen Bewertungsfaktoren berechnet.
- 24-Stundenvergleichsdaten bleiben Voraussetzung für die historische Prognosegüte.
- Null-Euro-Einfluss erzeugt keine künstlichen Gewichte.
- Sensorpfad verwendet nachweislich die zentrale Gewichtungsfunktion.
- Getrennte Bewertungsaufrufe für Verbrauch und Einspeisung bleiben erhalten.

## Nicht durchgeführte Prüfungen / Grenzen

Ein vollständiger Home-Assistant-Laufzeittest wurde in dieser Umgebung nicht durchgeführt. Deshalb kann die reale Anzeige nach einem HA-Neustart, das Verhalten mit den konkreten Recorder-/Entity-Daten der Installation und die tatsächlich gerenderte Animation im Browser nicht als live bestätigt gelten. Die automatisierten Tests prüfen den Backend-Datenfluss anhand des echten Forecast-Rechenergebnisses sowie den Frontend-Code/Syntax, ersetzen aber keinen laufenden Home-Assistant-Test.
